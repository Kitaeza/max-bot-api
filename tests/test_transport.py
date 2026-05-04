from collections.abc import AsyncGenerator

import httpx
import pytest
import respx

from max_bot_api.exceptions import (
    MaxAuthError,
    MaxRateLimitError,
    MaxTimeoutError,
    MaxTransportError,
)
from max_bot_api.models.messages import Message
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
