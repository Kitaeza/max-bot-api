# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/Kitaeza/python-max-bot/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Kitaeza/python-max-bot/releases/tag/v0.1.0
