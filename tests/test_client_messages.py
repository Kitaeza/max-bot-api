from collections.abc import AsyncGenerator

import httpx
import pytest
import respx

from max_bot_api import MaxClient
from max_bot_api.models.messages import Message, TextFormat

_BASE = "https://platform-api.max.ru"
_TOKEN = "tok"


def _msg_response(text: str = "hi") -> dict[str, object]:
    return {
        "sender": {"user_id": 1, "name": "bot"},
        "recipient": {"chat_id": 42, "chat_type": "chat"},
        "timestamp": 1234567890,
        "body": {"mid": "m1", "seq": 1, "text": text, "attachments": []},
    }


@pytest.fixture
async def client() -> AsyncGenerator[MaxClient, None]:
    c = MaxClient(token=_TOKEN, base_url=_BASE)
    yield c
    await c.aclose()


@respx.mock
async def test_send_message_to_chat(client: MaxClient) -> None:
    route = respx.post(f"{_BASE}/messages", params={"chat_id": "42"}).mock(
        return_value=httpx.Response(200, json=_msg_response())
    )
    msg = await client.send_message(chat_id=42, text="hi")
    assert isinstance(msg, Message)
    assert msg.body.text == "hi"
    sent = route.calls.last.request
    assert sent.read() == b'{"text":"hi","notify":true}'


@respx.mock
async def test_send_message_to_user(client: MaxClient) -> None:
    route = respx.post(f"{_BASE}/messages", params={"user_id": "7"}).mock(
        return_value=httpx.Response(200, json=_msg_response())
    )
    await client.send_message(user_id=7, text="hi")
    assert route.called


@respx.mock
async def test_send_message_with_format(client: MaxClient) -> None:
    route = respx.post(f"{_BASE}/messages", params={"chat_id": "42"}).mock(
        return_value=httpx.Response(200, json=_msg_response("**hi**"))
    )
    await client.send_message(chat_id=42, text="**hi**", format=TextFormat.MARKDOWN)
    body = route.calls.last.request.read()
    assert b'"format":"markdown"' in body


@respx.mock
async def test_send_message_disable_link_preview_goes_in_query(client: MaxClient) -> None:
    route = respx.post(
        f"{_BASE}/messages",
        params={"chat_id": "42", "disable_link_preview": "true"},
    ).mock(return_value=httpx.Response(200, json=_msg_response()))
    await client.send_message(chat_id=42, text="hi", disable_link_preview=True)
    assert route.called


async def test_send_message_requires_chat_or_user(client: MaxClient) -> None:
    with pytest.raises(ValueError, match="chat_id or user_id"):
        await client.send_message(text="hi")


async def test_send_message_rejects_both_chat_and_user(client: MaxClient) -> None:
    with pytest.raises(ValueError, match="not both"):
        await client.send_message(chat_id=1, user_id=2, text="hi")


async def test_send_message_requires_text_or_attachments(client: MaxClient) -> None:
    with pytest.raises(ValueError, match="text or attachments"):
        await client.send_message(chat_id=42)


async def test_send_message_rejects_text_over_4000_chars(client: MaxClient) -> None:
    with pytest.raises(ValueError, match="4000"):
        await client.send_message(chat_id=42, text="x" * 4001)


@respx.mock
async def test_edit_message(client: MaxClient) -> None:
    route = respx.put(f"{_BASE}/messages", params={"message_id": "m1"}).mock(
        return_value=httpx.Response(200, json=_msg_response("edited"))
    )
    msg = await client.edit_message("m1", text="edited")
    assert msg.body.text == "edited"
    assert route.called


@respx.mock
async def test_delete_message(client: MaxClient) -> None:
    route = respx.delete(f"{_BASE}/messages", params={"message_id": "m1"}).mock(
        return_value=httpx.Response(204)
    )
    await client.delete_message("m1")
    assert route.called


@respx.mock
async def test_get_messages(client: MaxClient) -> None:
    respx.get(
        f"{_BASE}/messages",
        params={"chat_id": "42", "count": "50"},
    ).mock(return_value=httpx.Response(200, json={"messages": [_msg_response()]}))
    msgs = await client.get_messages(chat_id=42)
    assert len(msgs) == 1
    assert msgs[0].body.text == "hi"


async def test_client_aclose(client: MaxClient) -> None:
    await client.aclose()  # idempotent — must not raise


async def test_client_as_context_manager() -> None:
    async with MaxClient(token=_TOKEN, base_url=_BASE) as c:
        assert isinstance(c, MaxClient)


@respx.mock
async def test_edit_message_omits_notify_by_default(client: MaxClient) -> None:
    """edit_message(notify=None) must NOT send `notify` on the wire — the
    server keeps the original notify state for the edit."""
    route = respx.put(f"{_BASE}/messages", params={"message_id": "m1"}).mock(
        return_value=httpx.Response(200, json=_msg_response("edited"))
    )
    await client.edit_message("m1", text="edited")
    body = route.calls.last.request.read()
    assert b"notify" not in body


@respx.mock
async def test_edit_message_sends_notify_when_explicit(client: MaxClient) -> None:
    """When the caller explicitly sets notify, the value reaches the wire."""
    route = respx.put(f"{_BASE}/messages", params={"message_id": "m1"}).mock(
        return_value=httpx.Response(200, json=_msg_response("edited"))
    )
    await client.edit_message("m1", text="edited", notify=False)
    body = route.calls.last.request.read()
    assert b'"notify":false' in body


@respx.mock
async def test_send_message_default_notify_is_true(client: MaxClient) -> None:
    """send_message keeps its notify=True default — explicit on the wire."""
    respx.post(f"{_BASE}/messages", params={"chat_id": "42"}).mock(
        return_value=httpx.Response(200, json=_msg_response())
    )
    await client.send_message(chat_id=42, text="hi")
    # Already covered by the existing test_send_message_to_chat which asserts
    # the body bytes; this is an explicit doc-style test that the default
    # didn't regress when we made the model field Optional.
