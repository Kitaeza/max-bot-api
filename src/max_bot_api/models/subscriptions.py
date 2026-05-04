"""Webhook subscription model — response from GET /subscriptions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Subscription(BaseModel):
    """An active webhook subscription.

    `update_types` uses `list[str]` rather than `list[UpdateType]` so a
    future server-side addition never crashes a get_subscriptions call.
    Request-side filtering (subscribe(update_types=...)) uses the strict
    UpdateType enum because the user controls that input.
    """

    model_config = ConfigDict(extra="ignore")

    url: str
    time: int
    update_types: list[str] | None = None
