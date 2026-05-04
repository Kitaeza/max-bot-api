"""Exception hierarchy for max-bot-api.

All exceptions raised by the library inherit from MaxError. API errors
(any non-2xx response) inherit from MaxAPIError. Network-level failures
inherit from MaxTransportError.
"""

from __future__ import annotations

import httpx


class MaxError(Exception):
    """Base class for everything raised by max-bot-api."""


class MaxAPIError(MaxError):
    """Raised for any non-2xx response from the Max API.

    Attributes:
        status_code: The HTTP status code from the response.
        code: The API's own error code (from response body), if present.
        message: The API's human-readable message, or "" if absent.
        response: The raw httpx.Response, exposed for advanced debugging.
    """

    def __init__(
        self,
        *,
        status_code: int,
        code: str | None,
        message: str,
        response: httpx.Response,
    ) -> None:
        super().__init__(f"[{status_code}] {message or '<no message>'}")
        self.status_code = status_code
        self.code = code
        self.message = message
        self.response = response


class MaxAuthError(MaxAPIError):
    """401 — token missing, invalid, or expired."""


class MaxNotFoundError(MaxAPIError):
    """404 — chat, message, or other resource not found."""


class MaxValidationError(MaxAPIError):
    """400 — request body or parameters rejected by the API."""


class MaxMethodNotAllowedError(MaxAPIError):
    """405 — wrong HTTP verb for this endpoint."""


class MaxRateLimitError(MaxAPIError):
    """429 — too many requests. Carries a parsed Retry-After if present."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str | None,
        message: str,
        response: httpx.Response,
        retry_after: float | None,
    ) -> None:
        super().__init__(
            status_code=status_code, code=code, message=message, response=response
        )
        self.retry_after = retry_after


class MaxServerError(MaxAPIError):
    """5xx — the Max API itself failed."""


class MaxServiceUnavailableError(MaxServerError):
    """503 — service temporarily unavailable."""


class MaxTransportError(MaxError):
    """The HTTP request never produced a response (connection error, DNS, etc.)."""


class MaxTimeoutError(MaxTransportError):
    """The HTTP request timed out before a response was received."""


_STATUS_MAP: dict[int, type[MaxAPIError]] = {
    400: MaxValidationError,
    401: MaxAuthError,
    404: MaxNotFoundError,
    405: MaxMethodNotAllowedError,
    429: MaxRateLimitError,
    503: MaxServiceUnavailableError,
}


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def raise_for_response(response: httpx.Response) -> None:
    """Raise the appropriate MaxAPIError subclass for a non-2xx response.

    No-op for 2xx responses. The response body is parsed once (best-effort)
    to populate `code` and `message`; bodies that aren't JSON or don't carry
    those fields just yield empty strings.
    """
    if 200 <= response.status_code < 300:
        return

    try:
        body = response.json()
    except ValueError:
        body = {}

    code = body.get("code") if isinstance(body, dict) else None
    message = body.get("message", "") if isinstance(body, dict) else ""

    cls = _STATUS_MAP.get(response.status_code)
    if cls is None:
        cls = MaxServerError if response.status_code >= 500 else MaxAPIError

    if cls is MaxRateLimitError:
        raise MaxRateLimitError(
            status_code=response.status_code,
            code=code,
            message=message,
            response=response,
            retry_after=_parse_retry_after(response.headers.get("Retry-After")),
        )

    raise cls(
        status_code=response.status_code,
        code=code,
        message=message,
        response=response,
    )
