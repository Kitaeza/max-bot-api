"""Attachment discriminated union.

All attachments share `{type, payload}`. The `type` field is the
discriminator; each subtype declares its own payload shape.

Variants use `extra="ignore"` so server-added fields don't break
parsing. The same models are also used inside `NewMessageBody` (a
request), where this means typos in attachment payload field names
are silently dropped instead of raising. We accept this asymmetry to
avoid duplicating every variant into request/response pairs — payload
field names are a small surface and stable. If this becomes a real
debugging burden, split the variants.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from max_bot_api.models.keyboards import InlineKeyboard


class AttachmentType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    INLINE_KEYBOARD = "inline_keyboard"


class _MediaPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    token: str
    url: str | None = None


class ImageAttachment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["image"] = "image"
    payload: _MediaPayload


class VideoAttachment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["video"] = "video"
    payload: _MediaPayload


class AudioAttachment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["audio"] = "audio"
    payload: _MediaPayload


class FileAttachment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["file"] = "file"
    payload: _MediaPayload


class InlineKeyboardAttachment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["inline_keyboard"] = "inline_keyboard"
    payload: InlineKeyboard


Attachment = Annotated[
    ImageAttachment | VideoAttachment | AudioAttachment | FileAttachment | InlineKeyboardAttachment,
    Field(discriminator="type"),
]
