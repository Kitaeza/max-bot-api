"""Pydantic models for the Max Bot API surface.

Re-exports public types so users can `from max_bot_api import Message`
rather than reaching into submodules. Internal-only types stay
unexported.
"""

from max_bot_api.models.attachments import (
    Attachment,
    AttachmentType,
    AudioAttachment,
    FileAttachment,
    ImageAttachment,
    InlineKeyboardAttachment,
    VideoAttachment,
)
from max_bot_api.models.keyboards import (
    Button,
    CallbackButton,
    ClipboardButton,
    InlineKeyboard,
    LinkButton,
    MessageButton,
    OpenAppButton,
    RequestContactButton,
    RequestGeoLocationButton,
)
from max_bot_api.models.messages import (
    Message,
    MessageBody,
    MessageRecipient,
    MessageSender,
    MessageStat,
    NewMessageBody,
    NewMessageLink,
    TextFormat,
)

__all__ = [
    "Attachment",
    "AttachmentType",
    "AudioAttachment",
    "Button",
    "CallbackButton",
    "ClipboardButton",
    "FileAttachment",
    "ImageAttachment",
    "InlineKeyboard",
    "InlineKeyboardAttachment",
    "LinkButton",
    "Message",
    "MessageBody",
    "MessageButton",
    "MessageRecipient",
    "MessageSender",
    "MessageStat",
    "NewMessageBody",
    "NewMessageLink",
    "OpenAppButton",
    "RequestContactButton",
    "RequestGeoLocationButton",
    "TextFormat",
    "VideoAttachment",
]
