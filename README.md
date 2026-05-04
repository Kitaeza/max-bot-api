# max-bot-api

[![PyPI](https://img.shields.io/pypi/v/max-bot-api.svg)](https://pypi.org/project/max-bot-api/)
[![Python](https://img.shields.io/pypi/pyversions/max-bot-api.svg)](https://pypi.org/project/max-bot-api/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Async Python client for the [Max messenger Bot API](https://dev.max.ru/docs-api).

A thin, stable, Pydantic-modeled wrapper. No bot framework, no FSM, no middleware — just the API surface you need to send messages, upload attachments, and poll for updates.

## Install

```bash
pip install max-bot-api
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

## What's in v0.1

| Feature | Status |
|---|---|
| Send / edit / delete messages | ✅ |
| Long-poll updates (`get_updates`) | ✅ |
| Image / video / audio / file uploads | ✅ |
| Inline keyboards | ✅ |
| Chat metadata (`get_chat`) | ✅ |
| HTML and Markdown formatting | ✅ |
| Typed exceptions per HTTP status | ✅ |
| Auto-retry / backoff | ⏳ v0.2 |
| Webhook subscription endpoints | ⏳ v0.3+ |
| Bot framework (handlers, FSM) | ❌ out of scope |

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

## Built with Claude

This project is developed in collaboration with [Claude](https://claude.com), Anthropic's AI assistant — design, code, and tests. Commits are co-authored. The repo ships with a [`CLAUDE.md`](CLAUDE.md) and [`.claude/settings.json`](.claude/) so any contributor running Claude on the codebase picks up the same conventions automatically. See the [v0.1 design](docs/design/0001-v0.1.md) for the full collaboration workflow.

## Links

- [Max Bot API docs](https://dev.max.ru/docs-api) — upstream reference
- [Design doc](docs/design/0001-v0.1.md) — what's in scope and what isn't
- [CHANGELOG](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT — see [LICENSE](LICENSE).
