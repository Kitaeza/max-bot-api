"""Update event models for long-polling and webhook delivery.

Each update has an `update_type` discriminator. UpdateList wraps a batch
of updates with the marker cursor returned by GET /updates.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from max_bot_api.models.messages import Message


class UpdateType(str, Enum):
    MESSAGE_CREATED = "message_created"
    MESSAGE_EDITED = "message_edited"
    MESSAGE_REMOVED = "message_removed"
    BOT_STARTED = "bot_started"
    BOT_ADDED = "bot_added"
    BOT_REMOVED = "bot_removed"


class _UpdateBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    timestamp: int


class MessageCreatedUpdate(_UpdateBase):
    update_type: Literal["message_created"] = "message_created"
    message: Message


class MessageEditedUpdate(_UpdateBase):
    update_type: Literal["message_edited"] = "message_edited"
    message: Message


class MessageRemovedUpdate(_UpdateBase):
    update_type: Literal["message_removed"] = "message_removed"
    message_id: str
    chat_id: int
    user_id: int


class _UserRef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: int
    name: str


class BotStartedUpdate(_UpdateBase):
    update_type: Literal["bot_started"] = "bot_started"
    chat_id: int
    user: _UserRef


class BotAddedUpdate(_UpdateBase):
    update_type: Literal["bot_added"] = "bot_added"
    chat_id: int
    user: _UserRef


class BotRemovedUpdate(_UpdateBase):
    update_type: Literal["bot_removed"] = "bot_removed"
    chat_id: int
    user: _UserRef


Update = Annotated[
    MessageCreatedUpdate
    | MessageEditedUpdate
    | MessageRemovedUpdate
    | BotStartedUpdate
    | BotAddedUpdate
    | BotRemovedUpdate,
    Field(discriminator="update_type"),
]


class UpdateList(BaseModel):
    """A batch of updates from GET /updates, plus the next marker cursor."""

    model_config = ConfigDict(extra="ignore")

    updates: list[Update] = []
    marker: int | None = None
