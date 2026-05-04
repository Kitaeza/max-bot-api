import httpx
import pytest

from max_bot_api.exceptions import (
    MaxAPIError,
    MaxAuthError,
    MaxError,
    MaxMethodNotAllowedError,
    MaxNotFoundError,
    MaxRateLimitError,
    MaxServerError,
    MaxServiceUnavailableError,
    MaxTimeoutError,
    MaxTransportError,
    MaxValidationError,
    raise_for_response,
)


def _response(
    status: int, body: dict[str, object] | None = None, headers: dict[str, str] | None = None
) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json=body if body is not None else {},
        headers=headers or {},
        request=httpx.Request("GET", "https://platform-api.max.ru/test"),
    )


def test_hierarchy_roots_at_max_error() -> None:
    assert issubclass(MaxAPIError, MaxError)
    assert issubclass(MaxTransportError, MaxError)
    assert issubclass(MaxTimeoutError, MaxTransportError)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, MaxValidationError),
        (401, MaxAuthError),
        (404, MaxNotFoundError),
        (405, MaxMethodNotAllowedError),
        (429, MaxRateLimitError),
        (500, MaxServerError),
        (502, MaxServerError),
        (503, MaxServiceUnavailableError),
    ],
)
def test_raise_for_response_maps_status(status: int, expected: type[MaxAPIError]) -> None:
    response = _response(status, {"code": "boom", "message": "kaboom"})
    with pytest.raises(expected) as info:
        raise_for_response(response)
    err = info.value
    assert err.status_code == status
    assert err.code == "boom"
    assert err.message == "kaboom"
    assert err.response is response


def test_raise_for_response_handles_empty_body() -> None:
    response = _response(401)
    with pytest.raises(MaxAuthError) as info:
        raise_for_response(response)
    assert info.value.code is None
    assert info.value.message == ""


def test_raise_for_response_passes_through_2xx() -> None:
    response = _response(200, {"ok": True})
    raise_for_response(response)  # must not raise


def test_rate_limit_parses_retry_after() -> None:
    response = _response(429, {"message": "slow down"}, {"Retry-After": "12"})
    with pytest.raises(MaxRateLimitError) as info:
        raise_for_response(response)
    assert info.value.retry_after == 12.0


def test_rate_limit_missing_retry_after_is_none() -> None:
    response = _response(429, {"message": "slow down"})
    with pytest.raises(MaxRateLimitError) as info:
        raise_for_response(response)
    assert info.value.retry_after is None


def test_unmapped_4xx_falls_back_to_max_api_error() -> None:
    response = _response(418, {"message": "teapot"})
    with pytest.raises(MaxAPIError) as info:
        raise_for_response(response)
    # 418 has no specific subclass — check it's the base, not one of the named subclasses
    assert type(info.value) is MaxAPIError
