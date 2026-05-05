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

from max_bot_api.exceptions import MaxBadResponseError
from max_bot_api.models._internal import _SendMessageResponse, _SimpleResponse
from max_bot_api.models.attachments import (
    Attachment,
    AudioAttachment,
    FileAttachment,
    ImageAttachment,
    VideoAttachment,
)
from max_bot_api.models.bot import BotInfo
from max_bot_api.models.chats import Chat, ChatAction, ChatMember, ChatMemberList
from max_bot_api.models.messages import (
    Message,
    NewMessageBody,
    NewMessageLink,
    TextFormat,
)
from max_bot_api.models.subscriptions import Subscription
from max_bot_api.models.updates import UpdateList, UpdateType
from max_bot_api.models.uploads import UploadEndpoint, UploadResult
from max_bot_api.retry import RetryPolicy
from max_bot_api.transport import Transport

_TEXT_MAX = 4000


class MaxClient:
    """Async client for the Max Bot API.

    Args:
        token: The bot's API token (from MasterBot in Max).
        base_url: API base URL. Override only for testing or proxy setups.
        timeout: Per-request timeout in seconds.
        transport: Custom httpx transport (mostly for tests).
        retry: Optional RetryPolicy. None (default) means no retries —
            single attempt per call, identical to v0.1.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://platform-api.max.ru",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
        retry: RetryPolicy | None = None,
    ) -> None:
        self._transport = Transport(
            token=token,
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            retry=retry,
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
        envelope = await self._transport.request(
            "POST",
            "/messages",
            params=params,
            json=body.model_dump(exclude_none=True, by_alias=True),
            idempotent=False,
            response_model=_SendMessageResponse,
        )
        return envelope.message

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
        envelope = await self._transport.request(
            "PUT",
            "/messages",
            params={"message_id": message_id},
            json=body.model_dump(exclude_none=True, by_alias=True),
            idempotent=False,
            response_model=_SendMessageResponse,
        )
        return envelope.message

    async def delete_message(self, message_id: str) -> None:
        """Delete a message by its mid."""
        await self._transport.request(
            "DELETE",
            "/messages",
            params={"message_id": message_id},
            idempotent=False,
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

        result = await self._transport.request("GET", "/messages", params=params, idempotent=True)
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
            "GET", "/updates", params=params, idempotent=True, response_model=UpdateList
        )

    # ── Chats ───────────────────────────────────────────────────────────

    async def get_chat(self, chat_id: int) -> Chat:
        """Fetch metadata for a single chat by ID."""
        return await self._transport.request(
            "GET", f"/chats/{chat_id}", idempotent=True, response_model=Chat
        )

    # ── Introspection ───────────────────────────────────────────────────

    async def get_me(self) -> BotInfo:
        """Fetch the authenticated bot's identity and metadata."""
        return await self._transport.request("GET", "/me", idempotent=True, response_model=BotInfo)

    async def get_chat_members(
        self,
        chat_id: int,
        *,
        user_ids: list[int] | None = None,
        marker: int | None = None,
        count: int = 20,
    ) -> ChatMemberList:
        """List members of a group chat.

        When `user_ids` is provided, the API treats it as a filter and
        ignores `marker`/`count`. Without it, results are paginated:
        pass back the returned `marker` on the next call.
        """
        if not 1 <= count <= 100:
            raise ValueError("count must be between 1 and 100")
        params: dict[str, object] = {
            "marker": marker,
            "count": count,
        }
        if user_ids:
            params["user_ids"] = ",".join(str(u) for u in user_ids)
        return await self._transport.request(
            "GET",
            f"/chats/{chat_id}/members",
            params=params,
            idempotent=True,
            response_model=ChatMemberList,
        )

    async def get_chat_admins(
        self,
        chat_id: int,
        *,
        marker: int | None = None,
    ) -> ChatMemberList:
        """List administrators of a group chat. Bot must itself be an admin."""
        return await self._transport.request(
            "GET",
            f"/chats/{chat_id}/members/admins",
            params={"marker": marker},
            idempotent=True,
            response_model=ChatMemberList,
        )

    async def get_my_chat_membership(self, chat_id: int) -> ChatMember:
        """Fetch the bot's own membership in a chat (admin status, permissions)."""
        return await self._transport.request(
            "GET",
            f"/chats/{chat_id}/members/me",
            idempotent=True,
            response_model=ChatMember,
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
            idempotent=True,
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

    # ── Webhook subscriptions ───────────────────────────────────────────

    async def get_subscriptions(self) -> list[Subscription]:
        """List all active webhook subscriptions for this bot."""
        result = await self._transport.request("GET", "/subscriptions", idempotent=True)
        return [Subscription.model_validate(s) for s in result.get("subscriptions", [])]

    async def subscribe(
        self,
        *,
        url: str,
        update_types: list[UpdateType] | None = None,
        secret: str | None = None,
    ) -> None:
        """Register a webhook URL to receive bot events.

        While a subscription is active, long-polling via get_updates()
        is disabled. The URL must be HTTPS; the API will reject http://.
        """
        self._validate_webhook_url(url)
        if secret is not None:
            self._validate_webhook_secret(secret)

        body: dict[str, object] = {"url": url}
        if update_types is not None:
            body["update_types"] = [t.value for t in update_types]
        if secret is not None:
            body["secret"] = secret

        result = await self._transport.request(
            "POST",
            "/subscriptions",
            json=body,
            idempotent=False,
            response_model=_SimpleResponse,
        )
        if not result.success:
            raise MaxBadResponseError(result.message)

    async def unsubscribe(self, *, url: str) -> None:
        """Remove a webhook subscription by URL."""
        result = await self._transport.request(
            "DELETE",
            "/subscriptions",
            params={"url": url},
            idempotent=False,
            response_model=_SimpleResponse,
        )
        if not result.success:
            raise MaxBadResponseError(result.message)

    # ── Action indicators ───────────────────────────────────────────────

    async def send_action(self, chat_id: int, action: ChatAction) -> None:
        """Send an activity indicator (typing, sending photo, ...) to a chat."""
        result = await self._transport.request(
            "POST",
            f"/chats/{chat_id}/actions",
            json={"action": action.value},
            idempotent=False,
            response_model=_SimpleResponse,
        )
        if not result.success:
            raise MaxBadResponseError(result.message)

    # ── Internal helpers ────────────────────────────────────────────────

    @staticmethod
    def _require_recipient(chat_id: int | None, user_id: int | None) -> None:
        if chat_id is None and user_id is None:
            raise ValueError("must provide chat_id or user_id")
        if chat_id is not None and user_id is not None:
            raise ValueError("provide chat_id or user_id, not both")

    @staticmethod
    def _require_content(text: str | None, attachments: list[Attachment] | None) -> None:
        if not text and not attachments:
            raise ValueError("must provide text or attachments")

    @staticmethod
    def _validate_webhook_url(url: str) -> None:
        if not url.startswith("https://"):
            raise ValueError("webhook url must start with https://")

    @staticmethod
    def _validate_webhook_secret(secret: str) -> None:
        if not 5 <= len(secret) <= 256:
            raise ValueError("webhook secret length must be between 5 and 256 characters")
        if not all(c.isalnum() or c == "-" for c in secret):
            raise ValueError("webhook secret may only contain A-Z, a-z, 0-9, and hyphen")
