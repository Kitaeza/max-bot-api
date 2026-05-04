"""Introspection methods on MaxClient: get_me, get_chat_members,
get_chat_admins, get_my_chat_membership."""

import httpx
import pytest
import respx

from max_bot_api import MaxClient

_BASE = "https://platform-api.max.ru"
_TOKEN = "test-token"

_ME_BODY = {
    "user_id": 1,
    "first_name": "TestBot",
    "username": "test_bot",
    "is_bot": True,
    "last_activity_time": 1700000000000,
}

_MEMBER_A = {
    "user_id": 100,
    "first_name": "Alice",
    "is_bot": False,
    "last_activity_time": 1700000000000,
}
_MEMBER_B = {
    "user_id": 101,
    "first_name": "Bob",
    "is_bot": False,
    "last_activity_time": 1700000000000,
}
_ADMIN_A = {**_MEMBER_A, "is_admin": True, "permissions": ["write", "pin_message"]}


@respx.mock
async def test_get_me_returns_bot_info() -> None:
    route = respx.get(f"{_BASE}/me").mock(return_value=httpx.Response(200, json=_ME_BODY))
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        me = await client.get_me()
    assert route.called
    assert me.user_id == 1
    assert me.username == "test_bot"


@respx.mock
async def test_get_chat_members_happy() -> None:
    body = {"members": [_MEMBER_A, _MEMBER_B], "marker": 555}
    route = respx.get(f"{_BASE}/chats/42/members").mock(return_value=httpx.Response(200, json=body))
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        page = await client.get_chat_members(42)
    assert route.called
    assert len(page.members) == 2
    assert page.marker == 555


@respx.mock
async def test_get_chat_members_passes_marker_and_count() -> None:
    body: dict[str, object] = {"members": [], "marker": None}
    route = respx.get(f"{_BASE}/chats/42/members", params={"marker": "555", "count": "50"}).mock(
        return_value=httpx.Response(200, json=body)
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        await client.get_chat_members(42, marker=555, count=50)
    assert route.called


@respx.mock
async def test_get_chat_members_user_ids_filter() -> None:
    body = {"members": [_MEMBER_A], "marker": None}
    route = respx.get(f"{_BASE}/chats/42/members").mock(return_value=httpx.Response(200, json=body))
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        page = await client.get_chat_members(42, user_ids=[100, 101])
    sent_url = str(route.calls.last.request.url)
    assert "user_ids" in sent_url
    assert page.members[0].user_id == 100


@pytest.mark.parametrize("bad", [0, -1, 101, 1000])
async def test_get_chat_members_rejects_count_out_of_range(bad: int) -> None:
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        with pytest.raises(ValueError, match="count"):
            await client.get_chat_members(42, count=bad)


@respx.mock
async def test_get_chat_admins_happy() -> None:
    body: dict[str, object] = {"members": [_ADMIN_A], "marker": None}
    route = respx.get(f"{_BASE}/chats/42/members/admins").mock(
        return_value=httpx.Response(200, json=body)
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        page = await client.get_chat_admins(42)
    assert route.called
    assert page.members[0].is_admin is True


@respx.mock
async def test_get_chat_admins_passes_marker() -> None:
    body: dict[str, object] = {"members": [], "marker": None}
    route = respx.get(f"{_BASE}/chats/42/members/admins", params={"marker": "999"}).mock(
        return_value=httpx.Response(200, json=body)
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        await client.get_chat_admins(42, marker=999)
    assert route.called


@respx.mock
async def test_get_my_chat_membership() -> None:
    body = {**_MEMBER_A, "is_admin": True, "join_time": 1600000000000}
    route = respx.get(f"{_BASE}/chats/42/members/me").mock(
        return_value=httpx.Response(200, json=body)
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        membership = await client.get_my_chat_membership(42)
    assert route.called
    assert membership.is_admin is True
    assert membership.join_time == 1600000000000
