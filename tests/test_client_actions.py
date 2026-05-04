"""Action indicator method on MaxClient: send_action."""

import httpx
import pytest
import respx

from max_bot_api import MaxClient
from max_bot_api.exceptions import MaxBadResponseError
from max_bot_api.models.chats import ChatAction

_BASE = "https://platform-api.max.ru"
_TOKEN = "test-token"


@pytest.mark.parametrize("action", list(ChatAction))
@respx.mock
async def test_send_action_happy(action: ChatAction) -> None:
    route = respx.post(f"{_BASE}/chats/42/actions").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        await client.send_action(42, action)
    assert route.called
    sent = route.calls.last.request.read()
    assert action.value.encode() in sent


@respx.mock
async def test_send_action_raises_on_success_false() -> None:
    respx.post(f"{_BASE}/chats/42/actions").mock(
        return_value=httpx.Response(200, json={"success": False, "message": "rate limited"})
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        with pytest.raises(MaxBadResponseError) as info:
            await client.send_action(42, ChatAction.TYPING_ON)
    assert info.value.message == "rate limited"
