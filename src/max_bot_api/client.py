"""MaxClient — the public entry point.

All API methods live here. Each method:
1. Validates inputs locally (mutual exclusion, length caps) and raises
   ValueError before any HTTP call.
2. Builds the request body via the matching Pydantic model so the wire
   format and validation rules stay in one place.
3. Delegates to Transport for the actual request.
"""

from __future__ import annotations

from typing import Literal

import httpx

from max_bot_api.models.attachments import Attachment
from max_bot_api.models.messages import (
    Message,
    NewMessageBody,
    NewMessageLink,
    TextFormat,
)
from max_bot_api.transport import Transport

_TEXT_MAX = 4000


class MaxClient:
    """Async client for the Max Bot API.

    Args:
        token: The bot's API token (from MasterBot in Max).
        base_url: API base URL. Override only for testing or proxy setups.
        timeout: Per-request timeout in seconds.
        transport: Custom httpx transport (mostly for tests).
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://platform-api.max.ru",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._transport = Transport(
            token=token, base_url=base_url, timeout=timeout, transport=transport
        )

    async def __aenter__(self) -> MaxClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._transport.aclose()

    # ── Messages ────────────────────────────────────────────────────────

    async def send_message(
        self,
        *,
        chat_id: int | None = None,
        user_id: int | None = None,
        text: str | None = None,
        format: TextFormat | Literal["html", "markdown"] | None = None,
        attachments: list[Attachment] | None = None,
        link: NewMessageLink | None = None,
        notify: bool = True,
        disable_link_preview: bool = False,
    ) -> Message:
        """Send a new message to a chat or user.

        Exactly one of `chat_id` or `user_id` must be provided. At least one
        of `text` or `attachments` must be non-empty. `text` is capped at
        4000 characters to match the API; longer text raises ValueError
        before the HTTP call.
        """
        self._require_recipient(chat_id, user_id)
        self._require_content(text, attachments)
        if text is not None and len(text) > _TEXT_MAX:
            raise ValueError(f"text exceeds {_TEXT_MAX} characters")

        body = NewMessageBody(
            text=text,
            attachments=attachments,
            link=link,
            notify=notify,
            format=TextFormat(format) if isinstance(format, str) else format,
        )
        params: dict[str, object] = {
            "chat_id": chat_id,
            "user_id": user_id,
            "disable_link_preview": "true" if disable_link_preview else None,
        }
        return await self._transport.request(
            "POST",
            "/messages",
            params=params,
            json=body.model_dump(exclude_none=True, by_alias=True),
            response_model=Message,
        )

    async def edit_message(
        self,
        message_id: str,
        *,
        text: str | None = None,
        format: TextFormat | Literal["html", "markdown"] | None = None,
        attachments: list[Attachment] | None = None,
        link: NewMessageLink | None = None,
        notify: bool | None = None,
    ) -> Message:
        """Edit an existing message by its mid."""
        self._require_content(text, attachments)
        if text is not None and len(text) > _TEXT_MAX:
            raise ValueError(f"text exceeds {_TEXT_MAX} characters")

        body = NewMessageBody(
            text=text,
            attachments=attachments,
            link=link,
            notify=notify,
            format=TextFormat(format) if isinstance(format, str) else format,
        )
        return await self._transport.request(
            "PUT",
            "/messages",
            params={"message_id": message_id},
            json=body.model_dump(exclude_none=True, by_alias=True),
            response_model=Message,
        )

    async def delete_message(self, message_id: str) -> None:
        """Delete a message by its mid."""
        await self._transport.request(
            "DELETE", "/messages", params={"message_id": message_id}
        )

    async def get_messages(
        self,
        *,
        chat_id: int | None = None,
        message_ids: list[str] | None = None,
        from_time: int | None = None,
        to_time: int | None = None,
        count: int = 50,
    ) -> list[Message]:
        """Retrieve messages from a chat or by ID."""
        params: dict[str, object] = {
            "chat_id": chat_id,
            "from": from_time,
            "to": to_time,
            "count": count,
        }
        if message_ids:
            params["message_ids"] = ",".join(message_ids)

        result = await self._transport.request("GET", "/messages", params=params)
        return [Message.model_validate(m) for m in result.get("messages", [])]

    # ── Internal helpers ────────────────────────────────────────────────

    @staticmethod
    def _require_recipient(chat_id: int | None, user_id: int | None) -> None:
        if chat_id is None and user_id is None:
            raise ValueError("must provide chat_id or user_id")
        if chat_id is not None and user_id is not None:
            raise ValueError("provide chat_id or user_id, not both")

    @staticmethod
    def _require_content(
        text: str | None, attachments: list[Attachment] | None
    ) -> None:
        if not text and not attachments:
            raise ValueError("must provide text or attachments")
