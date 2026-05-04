"""Message-related Pydantic models.

NewMessageBody is the request shape for POST /messages.
Message and its nested types describe the response.

Request models use extra="forbid" so user typos surface immediately.
Response models use extra="ignore" so server-side additions don't break
parsing.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from max_bot_api.models.attachments import Attachment


class TextFormat(str, Enum):
    HTML = "html"
    MARKDOWN = "markdown"


class NewMessageLink(BaseModel):
    """Reference to a message being replied to or forwarded."""

    model_config = ConfigDict(extra="forbid")

    type: str  # "reply" | "forward" — kept open until we see all values
    mid: str


class NewMessageBody(BaseModel):
    """Request body for POST /messages."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    text: str | None = None
    attachments: list[Attachment] | None = None
    link: NewMessageLink | None = None
    notify: bool = True
    format: TextFormat | None = None


class MessageSender(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: int
    name: str
    username: str | None = None
    is_bot: bool = False
    last_activity_time: int = 0


class MessageRecipient(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chat_id: int | None = None
    chat_type: str
    user_id: int | None = None


class MessageBody(BaseModel):
    """The text/attachments payload of a delivered message."""

    model_config = ConfigDict(extra="ignore")

    mid: str
    seq: int
    text: str | None = None
    attachments: list[Attachment] = []


class MessageStat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    views: int = 0


class Message(BaseModel):
    """A delivered message, as returned by the API."""

    model_config = ConfigDict(extra="ignore")

    sender: MessageSender
    recipient: MessageRecipient
    timestamp: int
    link: NewMessageLink | None = None
    body: MessageBody
    stat: MessageStat | None = None
    url: str | None = None
