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
