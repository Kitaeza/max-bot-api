"""Verify MaxClient passes the right `idempotent` flag at each call site
by observing retry behavior end-to-end."""

from collections.abc import Iterator
from unittest.mock import patch

import httpx
import pytest
import respx

from max_bot_api import MaxClient, RetryPolicy
from max_bot_api.exceptions import MaxServiceUnavailableError

_BASE = "https://platform-api.max.ru"
_TOKEN = "test-token-abc"

_CHAT_BODY = {
    "chat_id": 42,
    "type": "chat",
    "status": "active",
    "title": "Test",
    "last_event_time": 1234567890,
}


@pytest.fixture
def no_sleep() -> Iterator[None]:
    async def _noop(_: float) -> None:
        return None

    with patch("max_bot_api.transport.asyncio.sleep", _noop):
        yield


@pytest.fixture
def policy() -> RetryPolicy:
    return RetryPolicy(max_attempts=3, jitter=False)


@respx.mock
async def test_send_message_does_not_retry_on_5xx(policy: RetryPolicy, no_sleep: None) -> None:
    route = respx.post(f"{_BASE}/messages").mock(return_value=httpx.Response(503, json={}))
    async with MaxClient(_TOKEN, base_url=_BASE, retry=policy) as client:
        with pytest.raises(MaxServiceUnavailableError):
            await client.send_message(chat_id=42, text="hi")
    assert route.call_count == 1


@respx.mock
async def test_edit_message_does_not_retry_on_5xx(policy: RetryPolicy, no_sleep: None) -> None:
    route = respx.put(f"{_BASE}/messages").mock(return_value=httpx.Response(503, json={}))
    async with MaxClient(_TOKEN, base_url=_BASE, retry=policy) as client:
        with pytest.raises(MaxServiceUnavailableError):
            await client.edit_message("m1", text="hi")
    assert route.call_count == 1


@respx.mock
async def test_delete_message_does_not_retry_on_5xx(policy: RetryPolicy, no_sleep: None) -> None:
    route = respx.delete(f"{_BASE}/messages").mock(return_value=httpx.Response(503, json={}))
    async with MaxClient(_TOKEN, base_url=_BASE, retry=policy) as client:
        with pytest.raises(MaxServiceUnavailableError):
            await client.delete_message("m1")
    assert route.call_count == 1


@respx.mock
async def test_get_chat_retries_on_5xx_and_succeeds(policy: RetryPolicy, no_sleep: None) -> None:
    route = respx.get(f"{_BASE}/chats/42").mock(
        side_effect=[
            httpx.Response(503, json={}),
            httpx.Response(503, json={}),
            httpx.Response(200, json=_CHAT_BODY),
        ]
    )
    async with MaxClient(_TOKEN, base_url=_BASE, retry=policy) as client:
        chat = await client.get_chat(42)
    assert chat.chat_id == 42
    assert route.call_count == 3


@respx.mock
async def test_get_messages_retries_on_5xx(policy: RetryPolicy, no_sleep: None) -> None:
    route = respx.get(f"{_BASE}/messages").mock(
        side_effect=[
            httpx.Response(503, json={}),
            httpx.Response(200, json={"messages": []}),
        ]
    )
    async with MaxClient(_TOKEN, base_url=_BASE, retry=policy) as client:
        msgs = await client.get_messages(chat_id=42)
    assert msgs == []
    assert route.call_count == 2


@respx.mock
async def test_get_updates_retries_on_5xx(policy: RetryPolicy, no_sleep: None) -> None:
    route = respx.get(f"{_BASE}/updates").mock(
        side_effect=[
            httpx.Response(503, json={}),
            httpx.Response(200, json={"updates": [], "marker": 1}),
        ]
    )
    async with MaxClient(_TOKEN, base_url=_BASE, retry=policy) as client:
        result = await client.get_updates()
    assert result.marker == 1
    assert route.call_count == 2


@respx.mock
async def test_request_upload_url_retries_on_5xx(policy: RetryPolicy, no_sleep: None) -> None:
    route = respx.post(f"{_BASE}/uploads").mock(
        side_effect=[
            httpx.Response(503, json={}),
            httpx.Response(200, json={"url": "https://upload.example/abc"}),
        ]
    )
    async with MaxClient(_TOKEN, base_url=_BASE, retry=policy) as client:
        endpoint = await client.request_upload_url(type="image")
    assert endpoint.url == "https://upload.example/abc"
    assert route.call_count == 2


@respx.mock
async def test_no_policy_means_no_retry_on_get_chat(no_sleep: None) -> None:
    """retry=None must preserve v0.1 behavior even on idempotent reads."""
    route = respx.get(f"{_BASE}/chats/42").mock(return_value=httpx.Response(503, json={}))
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        with pytest.raises(MaxServiceUnavailableError):
            await client.get_chat(42)
    assert route.call_count == 1
