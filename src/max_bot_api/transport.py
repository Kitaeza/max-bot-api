"""HTTP transport layer.

Owns the httpx.AsyncClient, attaches auth headers, dispatches requests,
maps non-2xx responses to exceptions, and parses successful responses
into Pydantic models when the caller asks for one.

This stays a thin wrapper — no retry logic (deferred to v0.2), no
business rules. MaxClient builds on top.
"""

from __future__ import annotations

from typing import Any, TypeVar, overload

import httpx
from pydantic import BaseModel

from max_bot_api.exceptions import (
    MaxTimeoutError,
    MaxTransportError,
    raise_for_response,
)

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
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Authorization": token},
            transport=transport,
        )

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
        response_model: None = ...,
    ) -> Any: ...

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        response_model: type[_M] | None = None,
    ) -> Any:
        """Send an HTTP request to the Max API.

        Returns:
            - The parsed response_model instance if response_model is given
            - The decoded JSON dict if response_model is None and body is JSON
            - None for 204 No Content responses

        Raises:
            MaxAPIError subclass on non-2xx responses
            MaxTransportError on network failures
            MaxTimeoutError on timeouts
        """
        cleaned_params = (
            {k: v for k, v in params.items() if v is not None} if params else None
        )

        try:
            response = await self._client.request(
                method, path, params=cleaned_params, json=json
            )
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
