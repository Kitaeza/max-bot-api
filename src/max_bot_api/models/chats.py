"""Chat-related models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ChatType(str, Enum):
    DIALOG = "dialog"
    CHAT = "chat"
    CHANNEL = "channel"


class Chat(BaseModel):
    """A chat, group, or channel."""

    model_config = ConfigDict(extra="ignore")

    chat_id: int
    type: ChatType
    status: str  # "active" | "removed" | "left" | "closed" — open-coded
    title: str | None = None
    icon: dict[str, Any] | None = None
    last_event_time: int
    participants_count: int | None = None
    is_public: bool | None = None
    link: str | None = None
    description: str | None = None
    owner_id: int | None = None


class ChatAdminPermission(str, Enum):
    READ_ALL_MESSAGES = "read_all_messages"
    ADD_REMOVE_MEMBERS = "add_remove_members"
    ADD_ADMINS = "add_admins"
    CHANGE_CHAT_INFO = "change_chat_info"
    PIN_MESSAGE = "pin_message"
    WRITE = "write"
    CAN_CALL = "can_call"
    EDIT_LINK = "edit_link"
    POST_EDIT_DELETE_MESSAGE = "post_edit_delete_message"
    EDIT_MESSAGE = "edit_message"
    DELETE_MESSAGE = "delete_message"


class ChatAction(str, Enum):
    TYPING_ON = "typing_on"
    SENDING_PHOTO = "sending_photo"
    SENDING_VIDEO = "sending_video"
    SENDING_AUDIO = "sending_audio"
    SENDING_FILE = "sending_file"


class ChatMember(BaseModel):
    """A user (or bot) inside a chat. Returned by GET /chats/{chatId}/members
    and the admin / membership variants."""

    model_config = ConfigDict(extra="ignore")

    user_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    is_bot: bool
    last_activity_time: int
    description: str | None = None
    avatar_url: str | None = None
    full_avatar_url: str | None = None
    last_access_time: int | None = None
    join_time: int | None = None
    is_owner: bool | None = None
    is_admin: bool | None = None
    alias: str | None = None
    permissions: list[ChatAdminPermission] | None = None


class ChatMemberList(BaseModel):
    """Paginated chat-members response. Mirrors UpdateList shape."""

    model_config = ConfigDict(extra="ignore")

    members: list[ChatMember]
    marker: int | None = None
