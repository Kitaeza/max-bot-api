from collections.abc import AsyncGenerator, Iterator
from unittest.mock import patch

import httpx
import pytest
import respx

from max_bot_api.exceptions import (
    MaxAuthError,
    MaxRateLimitError,
    MaxServerError,
    MaxServiceUnavailableError,
    MaxTimeoutError,
    MaxTransportError,
)
from max_bot_api.models.messages import Message
from max_bot_api.retry import RetryPolicy
from max_bot_api.transport import Transport

_BASE = "https://platform-api.max.ru"
_TOKEN = "test-token-abc"


@pytest.fixture
async def transport() -> AsyncGenerator[Transport, None]:
    t = Transport(token=_TOKEN, base_url=_BASE, timeout=5.0)
    yield t
    await t.aclose()


@respx.mock
async def test_request_sends_auth_header(transport: Transport) -> None:
    route = respx.get(f"{_BASE}/test").mock(return_value=httpx.Response(200, json={"ok": True}))
    await transport.request("GET", "/test")
    assert route.called
    sent = route.calls.last.request
    assert sent.headers["Authorization"] == _TOKEN  # bare token, no Bearer prefix


@respx.mock
async def test_request_passes_query_params(transport: Transport) -> None:
    route = respx.get(f"{_BASE}/messages", params={"chat_id": "42"}).mock(
        return_value=httpx.Response(200, json={})
    )
    await transport.request("GET", "/messages", params={"chat_id": 42})
    assert route.called


@respx.mock
async def test_request_sends_json_body(transport: Transport) -> None:
    route = respx.post(f"{_BASE}/messages").mock(return_value=httpx.Response(200, json={}))
    await transport.request("POST", "/messages", json={"text": "hi"})
    assert route.calls.last.request.read() == b'{"text":"hi"}'


@respx.mock
async def test_request_returns_parsed_model(transport: Transport) -> None:
    response_body = {
        "sender": {"user_id": 1, "name": "Alice"},
        "recipient": {"chat_id": 42, "chat_type": "chat"},
        "timestamp": 1234567890,
        "body": {"mid": "m1", "seq": 1, "text": "hi", "attachments": []},
    }
    respx.post(f"{_BASE}/messages").mock(return_value=httpx.Response(200, json=response_body))
    msg = await transport.request("POST", "/messages", json={"text": "hi"}, response_model=Message)
    assert isinstance(msg, Message)
    assert msg.body.text == "hi"


@respx.mock
async def test_request_returns_raw_dict_when_no_model(transport: Transport) -> None:
    respx.get(f"{_BASE}/test").mock(return_value=httpx.Response(200, json={"ok": True}))
    result = await transport.request("GET", "/test")
    assert result == {"ok": True}


@respx.mock
async def test_request_returns_none_for_204(transport: Transport) -> None:
    respx.delete(f"{_BASE}/messages").mock(return_value=httpx.Response(204))
    result = await transport.request("DELETE", "/messages", params={"message_id": "m1"})
    assert result is None


@respx.mock
async def test_4xx_raises_typed_exception(transport: Transport) -> None:
    respx.get(f"{_BASE}/test").mock(
        return_value=httpx.Response(401, json={"code": "auth_failed", "message": "bad token"})
    )
    with pytest.raises(MaxAuthError) as info:
        await transport.request("GET", "/test")
    assert info.value.message == "bad token"


@respx.mock
async def test_429_carries_retry_after(transport: Transport) -> None:
    respx.get(f"{_BASE}/test").mock(
        return_value=httpx.Response(
            429, json={"message": "slow down"}, headers={"Retry-After": "5"}
        )
    )
    with pytest.raises(MaxRateLimitError) as info:
        await transport.request("GET", "/test")
    assert info.value.retry_after == 5.0


@respx.mock
async def test_network_error_wraps_to_max_transport_error(transport: Transport) -> None:
    respx.get(f"{_BASE}/test").mock(side_effect=httpx.ConnectError("DNS exploded"))
    with pytest.raises(MaxTransportError):
        await transport.request("GET", "/test")


@respx.mock
async def test_timeout_wraps_to_max_timeout_error(transport: Transport) -> None:
    respx.get(f"{_BASE}/test").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(MaxTimeoutError):
        await transport.request("GET", "/test")


@respx.mock
async def test_drops_none_query_params(transport: Transport) -> None:
    """Pydantic methods pass `chat_id=None, user_id=42` — None should not be serialized."""
    route = respx.get(f"{_BASE}/test", params={"user_id": "42"}).mock(
        return_value=httpx.Response(200, json={})
    )
    await transport.request("GET", "/test", params={"chat_id": None, "user_id": 42})
    assert route.called
    # Verify no chat_id key in the URL
    sent_url = str(route.calls.last.request.url)
    assert "chat_id" not in sent_url


# ── Retry behavior (v0.2) ───────────────────────────────────────────────


@pytest.fixture
def no_sleep() -> Iterator[None]:
    """Turn asyncio.sleep into a no-op so retry tests stay fast."""

    async def _noop(_: float) -> None:
        return None

    with patch("max_bot_api.transport.asyncio.sleep", _noop):
        yield


@pytest.fixture
async def transport_with_retry() -> AsyncGenerator[Transport, None]:
    t = Transport(
        token=_TOKEN,
        base_url=_BASE,
        timeout=5.0,
        retry=RetryPolicy(max_attempts=3, jitter=False),
    )
    yield t
    await t.aclose()


def test_service_unavailable_is_a_server_error() -> None:
    """The retry loop catches MaxServerError; ensure 503's subclass inherits."""
    assert issubclass(MaxServiceUnavailableError, MaxServerError)


@respx.mock
async def test_no_policy_does_not_retry_on_5xx(transport: Transport) -> None:
    route = respx.get(f"{_BASE}/test").mock(return_value=httpx.Response(503, json={}))
    with pytest.raises(MaxServiceUnavailableError):
        await transport.request("GET", "/test", idempotent=True)
    assert route.call_count == 1


@respx.mock
async def test_no_policy_does_not_retry_on_transport_error(transport: Transport) -> None:
    route = respx.get(f"{_BASE}/test").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(MaxTransportError):
        await transport.request("GET", "/test", idempotent=True)
    assert route.call_count == 1


@respx.mock
async def test_idempotent_5xx_retries_until_success(
    transport_with_retry: Transport, no_sleep: None
) -> None:
    route = respx.get(f"{_BASE}/test").mock(
        side_effect=[
            httpx.Response(503, json={}),
            httpx.Response(503, json={}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    result = await transport_with_retry.request("GET", "/test", idempotent=True)
    assert result == {"ok": True}
    assert route.call_count == 3


@respx.mock
async def test_non_idempotent_5xx_does_not_retry(
    transport_with_retry: Transport, no_sleep: None
) -> None:
    route = respx.get(f"{_BASE}/test").mock(return_value=httpx.Response(503, json={}))
    with pytest.raises(MaxServiceUnavailableError):
        await transport_with_retry.request("GET", "/test", idempotent=False)
    assert route.call_count == 1


@respx.mock
async def test_transport_error_retries_regardless_of_idempotent(
    transport_with_retry: Transport, no_sleep: None
) -> None:
    route = respx.get(f"{_BASE}/test").mock(
        side_effect=[
            httpx.ConnectError("boom"),
            httpx.ConnectError("boom"),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    result = await transport_with_retry.request("GET", "/test", idempotent=False)
    assert result == {"ok": True}
    assert route.call_count == 3


@respx.mock
async def test_429_retry_after_overrides_backoff_max(
    transport_with_retry: Transport,
) -> None:
    """Server says 60s; backoff_max is 30s; we must sleep at least 60s."""
    sleeps: list[float] = []

    async def _capture(seconds: float) -> None:
        sleeps.append(seconds)

    respx.get(f"{_BASE}/test").mock(
        side_effect=[
            httpx.Response(429, json={}, headers={"Retry-After": "60"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    with patch("max_bot_api.transport.asyncio.sleep", _capture):
        result = await transport_with_retry.request("GET", "/test", idempotent=True)
    assert result == {"ok": True}
    assert sleeps == [60.0]


@respx.mock
async def test_429_without_retry_after_uses_backoff(
    transport_with_retry: Transport,
) -> None:
    sleeps: list[float] = []

    async def _capture(seconds: float) -> None:
        sleeps.append(seconds)

    respx.get(f"{_BASE}/test").mock(
        side_effect=[
            httpx.Response(429, json={}),  # no Retry-After header
            httpx.Response(200, json={"ok": True}),
        ]
    )
    with patch("max_bot_api.transport.asyncio.sleep", _capture):
        await transport_with_retry.request("GET", "/test", idempotent=True)
    # First retry uses _backoff(policy, 1) = 1.0 (jitter off in fixture)
    assert sleeps == [1.0]


@respx.mock
async def test_4xx_never_retries(transport_with_retry: Transport, no_sleep: None) -> None:
    route = respx.get(f"{_BASE}/test").mock(return_value=httpx.Response(401, json={}))
    with pytest.raises(MaxAuthError):
        await transport_with_retry.request("GET", "/test", idempotent=True)
    assert route.call_count == 1


@respx.mock
async def test_exhausting_attempts_reraises_original_exception(
    transport_with_retry: Transport, no_sleep: None
) -> None:
    route = respx.get(f"{_BASE}/test").mock(return_value=httpx.Response(503, json={}))
    with pytest.raises(MaxServiceUnavailableError):
        await transport_with_retry.request("GET", "/test", idempotent=True)
    assert route.call_count == 3  # max_attempts


@respx.mock
async def test_500_is_retried_when_idempotent(
    transport_with_retry: Transport, no_sleep: None
) -> None:
    """MaxServerError covers the generic 5xx path, not just 503."""
    route = respx.get(f"{_BASE}/test").mock(
        side_effect=[
            httpx.Response(500, json={}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    result = await transport_with_retry.request("GET", "/test", idempotent=True)
    assert result == {"ok": True}
    assert route.call_count == 2
