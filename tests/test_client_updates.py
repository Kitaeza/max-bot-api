import httpx
import respx

from max_bot_api import MaxClient
from max_bot_api.models.updates import (
    MessageRemovedUpdate,
    UpdateList,
    UpdateType,
)

_BASE = "https://platform-api.max.ru"


def _empty_response() -> dict[str, object]:
    return {"updates": [], "marker": 100}


@respx.mock
async def test_get_updates_minimal() -> None:
    respx.get(f"{_BASE}/updates", params={"limit": "100", "timeout": "30"}).mock(
        return_value=httpx.Response(200, json=_empty_response())
    )
    async with MaxClient(token="t", base_url=_BASE) as c:
        result = await c.get_updates()
    assert isinstance(result, UpdateList)
    assert result.marker == 100
    assert result.updates == []


@respx.mock
async def test_get_updates_passes_marker() -> None:
    route = respx.get(
        f"{_BASE}/updates",
        params={"limit": "100", "timeout": "30", "marker": "50"},
    ).mock(return_value=httpx.Response(200, json=_empty_response()))
    async with MaxClient(token="t", base_url=_BASE) as c:
        await c.get_updates(marker=50)
    assert route.called


@respx.mock
async def test_get_updates_filters_by_type() -> None:
    route = respx.get(f"{_BASE}/updates").mock(
        return_value=httpx.Response(200, json=_empty_response())
    )
    async with MaxClient(token="t", base_url=_BASE) as c:
        await c.get_updates(types=[UpdateType.MESSAGE_CREATED, UpdateType.BOT_STARTED])
    sent_url = str(route.calls.last.request.url)
    assert "types=message_created" in sent_url
    assert "types=bot_started" in sent_url


@respx.mock
async def test_get_updates_parses_events() -> None:
    body = {
        "updates": [
            {
                "update_type": "message_removed",
                "timestamp": 1234567890,
                "message_id": "m1",
                "chat_id": 42,
                "user_id": 1,
            },
        ],
        "marker": 101,
    }
    respx.get(f"{_BASE}/updates").mock(return_value=httpx.Response(200, json=body))
    async with MaxClient(token="t", base_url=_BASE) as c:
        result = await c.get_updates()
    assert result.marker == 101
    assert isinstance(result.updates[0], MessageRemovedUpdate)
