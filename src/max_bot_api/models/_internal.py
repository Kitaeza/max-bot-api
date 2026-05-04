"""Internal helper models — not exported from the package root.

Kept separate from the public model files so code-search for "what
ships?" lands on the public surface, not on parsing scaffolding.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _SimpleResponse(BaseModel):
    """Parses the `{success, message}` envelope returned by the mutator
    endpoints (POST /subscriptions, DELETE /subscriptions, POST
    /chats/{chatId}/actions)."""

    model_config = ConfigDict(extra="ignore")

    success: bool
    message: str | None = None
