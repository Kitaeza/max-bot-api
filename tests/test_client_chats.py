import httpx
import respx

from max_bot_api import MaxClient
from max_bot_api.models.chats import Chat, ChatType

_BASE = "https://platform-api.max.ru"


@respx.mock
async def test_get_chat() -> None:
    body = {
        "chat_id": 42,
        "type": "channel",
        "status": "active",
        "title": "Test",
        "last_event_time": 1234567890,
    }
    respx.get(f"{_BASE}/chats/42").mock(return_value=httpx.Response(200, json=body))
    async with MaxClient(token="t", base_url=_BASE) as c:
        chat = await c.get_chat(42)
    assert isinstance(chat, Chat)
    assert chat.chat_id == 42
    assert chat.type == ChatType.CHANNEL
