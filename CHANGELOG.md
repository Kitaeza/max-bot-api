# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (Nothing yet — v0.5 work begins here.)

## [0.4.1] - 2026-05-05

### Fixed
- **`Message.sender` is now optional.** The live POST /messages and
  PUT /messages responses omit `sender` — the bot is the implicit
  sender on its own writes — so v0.4.0 still raised
  `ValidationError` after the envelope unwrap. Read paths
  (GET /messages, webhook updates) continue to populate it.

## [0.4.0] - 2026-05-05

### Fixed
- **`send_message` / `edit_message` no longer raise `ValidationError` on
  successful API responses.** The Max API wraps `POST /messages` and
  `PUT /messages` results under a top-level `message` key
  (`{"message": {sender, recipient, timestamp, body}}`); v0.1–v0.3
  parsed the outer dict directly as `Message` and raised on the
  "missing" required fields. The library now unwraps the envelope
  before parsing. Discovered when integrating against the live
  `platform-api.max.ru` endpoint — mocks in earlier tests had encoded
  the wrong shape, so the bug was invisible in CI.

## [0.3.0] - 2026-05-04

### Added
- **Bot introspection:** `get_me()` returns a `BotInfo`;
  `get_chat_members(chat_id)` and `get_chat_admins(chat_id)` return a
  paginated `ChatMemberList`; `get_my_chat_membership(chat_id)` returns
  a single `ChatMember` (useful for "am I admin here?" preflight).
- **Webhook subscriptions:** `subscribe(url, update_types?, secret?)`,
  `get_subscriptions()`, `unsubscribe(url)`. URL is locally validated
  to start with `https://`; secret is validated for length (5..256)
  and charset (`A-Za-z0-9-`). The library does not run a webhook
  server — that's still out of scope.
- **Action indicators:** `send_action(chat_id, ChatAction.TYPING_ON)`
  and four other documented actions (`SENDING_PHOTO`, `SENDING_VIDEO`,
  `SENDING_AUDIO`, `SENDING_FILE`).
- New types re-exported from `max_bot_api`: `BotInfo`, `BotCommand`,
  `ChatMember`, `ChatMemberList`, `ChatAdminPermission`, `ChatAction`,
  `Subscription`.
- New exception: `MaxBadResponseError` (inherits `MaxError`, not
  `MaxAPIError`) — raised when the API returns 2xx with `{success:
  false}` from the mutator endpoints (subscribe / unsubscribe /
  send_action).

## [0.2.0] - 2026-05-04

### Added
- `RetryPolicy` (frozen dataclass) for opt-in request retries. Pass via
  `MaxClient(token, retry=RetryPolicy(...))`. Default behavior is
  unchanged — no `retry=` argument means one attempt per call, identical
  to v0.1.
- Retry semantics: read methods (`get_messages`, `get_updates`,
  `get_chat`, `request_upload_url`) retry on `MaxServerError` /
  `MaxRateLimitError` / `MaxTransportError`. Write methods
  (`send_message`, `edit_message`, `delete_message`, the upload POST)
  only retry on `MaxTransportError` — a 5xx during a write may have
  succeeded server-side and a blind retry would double-apply.
- 429 responses honor `Retry-After`; the header is never clamped by
  `backoff_max`.

## [0.1.0] - 2026-05-04

### Added
- `MaxClient` async client with `send_message`, `edit_message`, `delete_message`, `get_messages`.
- `get_updates` long-polling with marker cursor wrapped in `UpdateList`.
- `get_chat` metadata fetch.
- Two-step upload primitives (`request_upload_url`, `upload_file`) plus
  one-call helpers (`upload_image`, `upload_video`, `upload_audio`,
  `upload_file_attachment`) returning typed `Attachment` instances.
- Inline keyboards with row/column limit enforcement at validation time.
- Pydantic v2 models for messages, attachments, keyboards, chats, updates.
- Exception hierarchy mapped from HTTP status: `MaxAuthError` (401),
  `MaxNotFoundError` (404), `MaxValidationError` (400),
  `MaxMethodNotAllowedError` (405), `MaxRateLimitError` (429,
  with `retry_after`), `MaxServerError` (5xx),
  `MaxServiceUnavailableError` (503).
- Transport-level errors wrapped as `MaxTransportError` /
  `MaxTimeoutError`.
- Full type coverage with `py.typed` marker.
- MIT license, hatchling build, ruff + mypy --strict in CI.

[Unreleased]: https://github.com/Kitaeza/python-max-bot/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Kitaeza/python-max-bot/releases/tag/v0.3.0
[0.2.0]: https://github.com/Kitaeza/python-max-bot/releases/tag/v0.2.0
[0.1.0]: https://github.com/Kitaeza/python-max-bot/releases/tag/v0.1.0
