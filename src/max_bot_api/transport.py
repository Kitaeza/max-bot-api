"""HTTP transport layer.

Owns the httpx.AsyncClient, attaches auth headers, dispatches requests,
maps non-2xx responses to exceptions, and parses successful responses
into Pydantic models when the caller asks for one.

When constructed with a RetryPolicy, the request method retries
according to the policy. The policy is opt-in; passing retry=None
preserves v0.1 single-attempt behavior byte-for-byte.
"""

from __future__ import annotations

import asyncio
from typing import Any, TypeVar, overload

import httpx
from pydantic import BaseModel

from max_bot_api.exceptions import (
    MaxRateLimitError,
    MaxServerError,
    MaxTimeoutError,
    MaxTransportError,
    raise_for_response,
)
from max_bot_api.retry import RetryPolicy, _backoff

_M = TypeVar("_M", bound=BaseModel)


class Transport:
    """Async HTTP wrapper for the Max API.

    Use as an async context manager or call aclose() explicitly.
    """

    def __init__(
        self,
        *,
        token: str,
        base_url: str = "https://platform-api.max.ru",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
        retry: RetryPolicy | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Authorization": token},
            transport=transport,
        )
        self._retry = retry

    async def __aenter__(self) -> Transport:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    @overload
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = ...,
        json: Any | None = ...,
        idempotent: bool = ...,
        response_model: type[_M],
    ) -> _M: ...

    @overload
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = ...,
        json: Any | None = ...,
        idempotent: bool = ...,
        response_model: None = ...,
    ) -> Any: ...

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        idempotent: bool = False,
        response_model: type[_M] | None = None,
    ) -> Any:
        """Send an HTTP request to the Max API.

        Args:
            idempotent: If True, the call is safe to replay (read methods,
                upload-URL requests). On a 5xx response, the retry policy
                will retry. If False (default), 5xx responses are raised
                without retry — protects writes from double-applying.

        Returns:
            - The parsed response_model instance if response_model is given
            - The decoded JSON dict if response_model is None and body is JSON
            - None for 204 No Content responses

        Raises:
            MaxAPIError subclass on non-2xx responses
            MaxTransportError on network failures
            MaxTimeoutError on timeouts
        """
        if self._retry is None:
            return await self._do_request(method, path, params, json, response_model)

        policy = self._retry
        for attempt in range(1, policy.max_attempts + 1):
            try:
                return await self._do_request(method, path, params, json, response_model)
            except MaxRateLimitError as exc:
                if attempt == policy.max_attempts:
                    raise
                wait = max(exc.retry_after or 0.0, _backoff(policy, attempt))
                await asyncio.sleep(wait)
            except MaxServerError:
                if attempt == policy.max_attempts or not idempotent:
                    raise
                await asyncio.sleep(_backoff(policy, attempt))
            except MaxTransportError:
                if attempt == policy.max_attempts:
                    raise
                await asyncio.sleep(_backoff(policy, attempt))

        # Unreachable: the loop above always returns or raises on the final
        # attempt. Present so mypy sees a definite return path.
        raise AssertionError("retry loop exited without returning or raising")

    async def _do_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None,
        json: Any | None,
        response_model: type[_M] | None,
    ) -> Any:
        cleaned_params = {k: v for k, v in params.items() if v is not None} if params else None

        try:
            response = await self._client.request(method, path, params=cleaned_params, json=json)
        except httpx.TimeoutException as exc:
            raise MaxTimeoutError(str(exc)) from exc
        except httpx.TransportError as exc:
            raise MaxTransportError(str(exc)) from exc

        raise_for_response(response)

        if response.status_code == 204 or not response.content:
            return None

        body = response.json()
        if response_model is not None:
            return response_model.model_validate(body)
        return body
