"""Webhook subscription methods on MaxClient: get_subscriptions,
subscribe, unsubscribe."""

import httpx
import pytest
import respx

from max_bot_api import MaxClient
from max_bot_api.exceptions import MaxBadResponseError
from max_bot_api.models.updates import UpdateType

_BASE = "https://platform-api.max.ru"
_TOKEN = "test-token"


@respx.mock
async def test_get_subscriptions_happy() -> None:
    body = {
        "subscriptions": [
            {
                "url": "https://example.com/wh",
                "time": 1700000000000,
                "update_types": ["message_created"],
            }
        ]
    }
    route = respx.get(f"{_BASE}/subscriptions").mock(return_value=httpx.Response(200, json=body))
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        subs = await client.get_subscriptions()
    assert route.called
    assert len(subs) == 1
    assert subs[0].url == "https://example.com/wh"


@respx.mock
async def test_get_subscriptions_empty() -> None:
    respx.get(f"{_BASE}/subscriptions").mock(
        return_value=httpx.Response(200, json={"subscriptions": []})
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        subs = await client.get_subscriptions()
    assert subs == []


@respx.mock
async def test_subscribe_happy() -> None:
    route = respx.post(f"{_BASE}/subscriptions").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        await client.subscribe(
            url="https://example.com/wh",
            update_types=[UpdateType.MESSAGE_CREATED],
            secret="abc-12345",
        )
    assert route.called
    body = route.calls.last.request.read()
    assert b"https://example.com/wh" in body
    assert b"message_created" in body
    assert b"abc-12345" in body


@respx.mock
async def test_subscribe_minimal() -> None:
    route = respx.post(f"{_BASE}/subscriptions").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        await client.subscribe(url="https://example.com/wh")
    assert route.called


async def test_subscribe_rejects_non_https_url() -> None:
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        with pytest.raises(ValueError, match="https://"):
            await client.subscribe(url="http://example.com/wh")


async def test_subscribe_rejects_bare_hostname() -> None:
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        with pytest.raises(ValueError, match="https://"):
            await client.subscribe(url="example.com/wh")


@pytest.mark.parametrize(
    "secret",
    ["abc", "a" * 4, "a" * 257, "abc!", "abc def", "abc/def"],
)
async def test_subscribe_rejects_bad_secret(secret: str) -> None:
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        with pytest.raises(ValueError, match="secret"):
            await client.subscribe(url="https://example.com/wh", secret=secret)


@pytest.mark.parametrize(
    "secret",
    ["abcde", "abcde-12345", "A" * 256, "ABCdef-123"],
)
@respx.mock
async def test_subscribe_accepts_valid_secret(secret: str) -> None:
    respx.post(f"{_BASE}/subscriptions").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        await client.subscribe(url="https://example.com/wh", secret=secret)


@respx.mock
async def test_subscribe_raises_on_success_false() -> None:
    respx.post(f"{_BASE}/subscriptions").mock(
        return_value=httpx.Response(200, json={"success": False, "message": "URL unreachable"})
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        with pytest.raises(MaxBadResponseError) as info:
            await client.subscribe(url="https://example.com/wh")
    assert info.value.message == "URL unreachable"


@respx.mock
async def test_unsubscribe_happy() -> None:
    route = respx.delete(f"{_BASE}/subscriptions", params={"url": "https://example.com/wh"}).mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        await client.unsubscribe(url="https://example.com/wh")
    assert route.called


@respx.mock
async def test_unsubscribe_raises_on_success_false() -> None:
    respx.delete(f"{_BASE}/subscriptions").mock(
        return_value=httpx.Response(200, json={"success": False, "message": "no such subscription"})
    )
    async with MaxClient(_TOKEN, base_url=_BASE) as client:
        with pytest.raises(MaxBadResponseError) as info:
            await client.unsubscribe(url="https://example.com/wh")
    assert info.value.message == "no such subscription"
