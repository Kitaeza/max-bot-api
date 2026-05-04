"""Bot-info models — response from GET /me."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BotCommand(BaseModel):
    """A single command entry in BotInfo.commands."""

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str | None = None


class BotInfo(BaseModel):
    """Bot identity and metadata. Response from GET /me."""

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
    commands: list[BotCommand] | None = None
    name: str | None = None  # API marks this deprecated; keep for compat
