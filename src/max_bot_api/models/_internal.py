"""Internal helper models — not exported from the package root.

Kept separate from the public model files so code-search for "what
ships?" lands on the public surface, not on parsing scaffolding.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from max_bot_api.models.messages import Message


class _SimpleResponse(BaseModel):
    """Parses the `{success, message}` envelope returned by the mutator
    endpoints (POST /subscriptions, DELETE /subscriptions, POST
    /chats/{chatId}/actions)."""

    model_config = ConfigDict(extra="ignore")

    success: bool
    message: str | None = None


class _SendMessageResponse(BaseModel):
    """Parses the `{message: Message}` envelope returned by POST /messages
    and PUT /messages. The Max API wraps the message body in a top-level
    `message` key; we unwrap and return the inner `Message` from
    `send_message` / `edit_message`."""

    model_config = ConfigDict(extra="ignore")

    message: Message
