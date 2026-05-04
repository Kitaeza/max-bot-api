# python-max-bot

[![PyPI](https://img.shields.io/pypi/v/python-max-bot.svg)](https://pypi.org/project/python-max-bot/)
[![Python](https://img.shields.io/pypi/pyversions/python-max-bot.svg)](https://pypi.org/project/python-max-bot/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Async Python client for the [Max messenger Bot API](https://dev.max.ru/docs-api).

A thin, stable, Pydantic-modeled wrapper. No bot framework, no FSM, no middleware — just the typed API surface for messaging, uploads, updates, webhooks, and chat introspection.

## Install

```bash
pip install python-max-bot
```

## Quickstart

```python
import asyncio
from max_bot_api import MaxClient

async def main():
    async with MaxClient(token="YOUR_BOT_TOKEN") as client:
        # Send a plain message
        await client.send_message(chat_id=42, text="Hello, Max!")

        # Send a message with an image
        with open("photo.jpg", "rb") as f:
            img = await client.upload_image(f.read(), filename="photo.jpg")
        await client.send_message(
            chat_id=42,
            text="<b>Look at this</b>",
            format="html",
            attachments=[img],
        )

asyncio.run(main())
```

## Features

| Feature | Status |
|---|---|
| Send / edit / delete messages | ✅ |
| Long-poll updates (`get_updates`) | ✅ |
| Image / video / audio / file uploads | ✅ |
| Inline keyboards | ✅ |
| Chat metadata (`get_chat`) | ✅ |
| HTML and Markdown formatting | ✅ |
| Typed exceptions per HTTP status | ✅ |
| Auto-retry / backoff | ✅ |
| Bot introspection (`get_me`, members, admins) | ✅ |
| Webhook subscription endpoints | ✅ |
| Action indicators (typing, sending photo, …) | ✅ |
| Bot framework (handlers, FSM) | ❌ out of scope |

## Polling for updates

Long-poll the API and walk the marker cursor:

```python
import asyncio
from max_bot_api import MaxClient

async def main():
    async with MaxClient(token="YOUR_BOT_TOKEN") as client:
        marker: int | None = None
        while True:
            page = await client.get_updates(marker=marker, timeout=30)
            for update in page.updates:
                # `update` is a discriminated-union Pydantic model — check
                # `update.update_type` or use isinstance on the subtypes.
                print(update)
            marker = page.marker

asyncio.run(main())
```

`get_updates(timeout=30)` blocks server-side for up to 30 seconds waiting for new events; pass the returned `marker` back on the next call to advance the cursor. While a webhook subscription is active, this method is disabled — pick one transport, not both.

## Introspection

```python
from max_bot_api import MaxClient

async with MaxClient(token) as client:
    # Who am I?
    me = await client.get_me()
    print(me.user_id, me.username, me.first_name)

    # Walk a paginated member list
    page = await client.get_chat_members(chat_id=42, count=50)
    while True:
        for member in page.members:
            print(member.user_id, member.first_name)
        if page.marker is None:
            break
        page = await client.get_chat_members(chat_id=42, marker=page.marker, count=50)

    # Filter mode — fetch only specific users (overrides marker/count server-side)
    page = await client.get_chat_members(chat_id=42, user_ids=[100, 200])

    # Admins (bot must itself be an admin in the chat)
    admins = await client.get_chat_admins(chat_id=42)
    for admin in admins.members:
        print(admin.user_id, admin.permissions)

    # "Am I admin here?" preflight before doing admin-only operations
    self_membership = await client.get_my_chat_membership(42)
    if self_membership.is_admin:
        ...
```

## Action indicators

Send a typing or sending-photo indicator while you do work:

```python
from max_bot_api import MaxClient, ChatAction

async with MaxClient(token) as client:
    await client.send_action(42, ChatAction.TYPING_ON)
    reply = await compute_expensive_reply(...)
    await client.send_message(chat_id=42, text=reply)
```

Available actions: `TYPING_ON`, `SENDING_PHOTO`, `SENDING_VIDEO`, `SENDING_AUDIO`, `SENDING_FILE`.

## Errors

```python
from max_bot_api import (
    MaxClient,
    MaxAuthError,
    MaxRateLimitError,
    MaxTransportError,
)

async with MaxClient(token=...) as client:
    try:
        await client.send_message(chat_id=42, text="hi")
    except MaxAuthError:
        # Bad token — surface to user
        ...
    except MaxRateLimitError as e:
        await asyncio.sleep(e.retry_after or 1)
    except MaxTransportError:
        # Network problem; retry your way
        ...
```

`subscribe`, `unsubscribe`, and `send_action` can also raise **`MaxBadResponseError`** — the API returned 2xx but with `{"success": false, "message": "..."}` in the body. It inherits from `MaxError` (not `MaxAPIError`, since the HTTP call itself succeeded), and `.message` carries the server's explanation.

## Retries

Retries are opt-in. Pass a `RetryPolicy` to the client constructor:

```python
from max_bot_api import MaxClient, RetryPolicy

async with MaxClient(token, retry=RetryPolicy()) as client:
    await client.get_chat(42)               # retries on 5xx and transport errors
    await client.send_message(chat_id=42, text="hi")  # only retries on transport errors
```

The default policy: 3 attempts, exponential backoff (1s, 2s, 4s with ±25% jitter), capped at 30s per wait. Tune via `RetryPolicy(max_attempts=..., backoff_initial=..., backoff_multiplier=..., backoff_max=..., jitter=...)`.

Read methods (`get_messages`, `get_updates`, `get_chat`, `request_upload_url`) retry on both transport errors and 5xx responses. Write methods (`send_message`, `edit_message`, `delete_message`, the upload POST) only retry on transport errors — a 5xx during a write could mean the server processed it, so blind retry could double-apply.

429 responses always retry. The library waits at least as long as the server's `Retry-After` header asks; `backoff_max` does **not** clamp the server's instruction.

Without `retry=`, behavior is identical to v0.1 — one attempt per call.

## Webhooks

Register and manage webhook subscriptions (the receiver server is yours to run):

```python
from max_bot_api import MaxClient, UpdateType

async with MaxClient(token) as client:
    await client.subscribe(
        url="https://my.server/max-webhook",
        update_types=[UpdateType.MESSAGE_CREATED],
        secret="my-shared-secret-12345",
    )

    subs = await client.get_subscriptions()
    for s in subs:
        print(s.url, s.update_types)

    await client.unsubscribe(url="https://my.server/max-webhook")
```

The URL must be HTTPS — `subscribe()` raises `ValueError` on `http://` locally before any network call. While a subscription is active, long-polling via `get_updates()` is disabled.

## Built with Claude

This project is developed in collaboration with [Claude](https://claude.com), Anthropic's AI assistant — design, code, and tests. Commits are co-authored. The repo ships with a [`CLAUDE.md`](CLAUDE.md) and [`.claude/settings.json`](.claude/) so any contributor running Claude on the codebase picks up the same conventions automatically. See the [v0.1 design](docs/design/0001-v0.1.md) for the full collaboration workflow.

## Links

- [Max Bot API docs](https://dev.max.ru/docs-api) — upstream reference
- [Design doc](docs/design/0001-v0.1.md) — what's in scope and what isn't
- [CHANGELOG](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT — see [LICENSE](LICENSE).
