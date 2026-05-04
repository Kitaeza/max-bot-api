"""MaxClient — the public entry point.

All API methods live here. Each method:
1. Validates inputs locally (mutual exclusion, length caps) and raises
   ValueError before any HTTP call.
2. Builds the request body via the matching Pydantic model so the wire
   format and validation rules stay in one place.
3. Delegates to Transport for the actual request.
"""

from __future__ import annotations

from typing import BinaryIO, Literal

import httpx

from max_bot_api.models.attachments import (
    Attachment,
    AudioAttachment,
    FileAttachment,
    ImageAttachment,
    VideoAttachment,
)
from max_bot_api.models.chats import Chat
from max_bot_api.models.messages import (
    Message,
    NewMessageBody,
    NewMessageLink,
    TextFormat,
)
from max_bot_api.models.updates import UpdateList, UpdateType
from max_bot_api.models.uploads import UploadEndpoint, UploadResult
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

    # ── Updates ─────────────────────────────────────────────────────────

    async def get_updates(
        self,
        *,
        limit: int = 100,
        timeout: int = 30,
        marker: int | None = None,
        types: list[UpdateType] | None = None,
    ) -> UpdateList:
        """Long-poll for updates.

        `timeout` is the long-poll wait in seconds — the request blocks
        server-side until an update arrives or the timeout elapses.
        Pass back the returned `marker` on the next call to advance the
        cursor.
        """
        params: dict[str, object] = {
            "limit": limit,
            "timeout": timeout,
            "marker": marker,
        }
        if types:
            # httpx encodes list values as repeated query params (?types=a&types=b)
            params["types"] = [t.value for t in types]

        return await self._transport.request(
            "GET", "/updates", params=params, response_model=UpdateList
        )

    # ── Chats ───────────────────────────────────────────────────────────

    async def get_chat(self, chat_id: int) -> Chat:
        """Fetch metadata for a single chat by ID."""
        return await self._transport.request(
            "GET", f"/chats/{chat_id}", response_model=Chat
        )

    # ── Uploads ─────────────────────────────────────────────────────────

    async def request_upload_url(
        self,
        *,
        type: Literal["image", "video", "audio", "file"],
    ) -> UploadEndpoint:
        """Step 1 of attachment upload: ask the API where to send the file."""
        return await self._transport.request(
            "POST",
            "/uploads",
            params={"type": type},
            response_model=UploadEndpoint,
        )

    async def upload_file(
        self,
        upload_url: str,
        content: bytes | BinaryIO,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> UploadResult:
        """Step 2 of attachment upload: POST the bytes to the URL from step 1.

        The upload URL is on a different host (the upload service, not the
        API), so we use a fresh httpx call rather than going through the
        bound transport.
        """
        files = {
            "file": (
                filename or "file",
                content,
                content_type or "application/octet-stream",
            )
        }
        async with httpx.AsyncClient(timeout=300.0) as upload_client:
            response = await upload_client.post(upload_url, files=files)
            response.raise_for_status()
            return UploadResult.model_validate(response.json())

    async def upload_image(
        self,
        content: bytes | BinaryIO,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> ImageAttachment:
        """One-call helper: request URL, upload bytes, return ImageAttachment.

        content_type defaults to None — the upload host infers from bytes.
        Pass explicitly (e.g. "image/png") if the host requires it.
        """
        endpoint = await self.request_upload_url(type="image")
        result = await self.upload_file(
            endpoint.url, content, filename=filename, content_type=content_type
        )
        return ImageAttachment.model_validate({"payload": {"token": result.token}})

    async def upload_video(
        self,
        content: bytes | BinaryIO,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> VideoAttachment:
        """One-call helper: request URL, upload bytes, return VideoAttachment.

        content_type defaults to None — the upload host infers from bytes.
        Pass explicitly (e.g. "video/webm") if the host requires it.
        """
        endpoint = await self.request_upload_url(type="video")
        result = await self.upload_file(
            endpoint.url, content, filename=filename, content_type=content_type
        )
        return VideoAttachment.model_validate({"payload": {"token": result.token}})

    async def upload_audio(
        self,
        content: bytes | BinaryIO,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> AudioAttachment:
        """One-call helper: request URL, upload bytes, return AudioAttachment.

        content_type defaults to None — the upload host infers from bytes.
        Pass explicitly (e.g. "audio/ogg") if the host requires it.
        """
        endpoint = await self.request_upload_url(type="audio")
        result = await self.upload_file(
            endpoint.url, content, filename=filename, content_type=content_type
        )
        return AudioAttachment.model_validate({"payload": {"token": result.token}})

    async def upload_file_attachment(
        self,
        content: bytes | BinaryIO,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> FileAttachment:
        """One-call helper for arbitrary files."""
        endpoint = await self.request_upload_url(type="file")
        result = await self.upload_file(
            endpoint.url,
            content,
            filename=filename,
            content_type=content_type or "application/octet-stream",
        )
        return FileAttachment.model_validate({"payload": {"token": result.token}})

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
