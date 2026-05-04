"""Pydantic models for the Max Bot API surface.

Re-exports public types so users can `from max_bot_api import Message`
rather than reaching into submodules. Internal-only types stay
unexported.
"""

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
    "Message",
    "MessageBody",
    "MessageRecipient",
    "MessageSender",
    "MessageStat",
    "NewMessageBody",
    "NewMessageLink",
    "TextFormat",
]
