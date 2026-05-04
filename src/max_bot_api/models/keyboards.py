"""Inline keyboard models.

Buttons are a discriminated union on the `type` field. The keyboard
itself enforces Max's row/column limits (≤7 buttons per row, ≤30 rows).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _ButtonBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


class CallbackButton(_ButtonBase):
    type: Literal["callback"] = "callback"
    payload: str
    intent: str | None = None  # "default" | "positive" | "negative"


class LinkButton(_ButtonBase):
    type: Literal["link"] = "link"
    url: str


class RequestContactButton(_ButtonBase):
    type: Literal["request_contact"] = "request_contact"


class RequestGeoLocationButton(_ButtonBase):
    type: Literal["request_geo_location"] = "request_geo_location"
    quick: bool | None = None


class OpenAppButton(_ButtonBase):
    type: Literal["open_app"] = "open_app"
    web_app: str | None = None
    contact_id: int | None = None


class MessageButton(_ButtonBase):
    type: Literal["message"] = "message"


class ClipboardButton(_ButtonBase):
    type: Literal["clipboard"] = "clipboard"
    copy_text: str


Button = Annotated[
    CallbackButton
    | LinkButton
    | RequestContactButton
    | RequestGeoLocationButton
    | OpenAppButton
    | MessageButton
    | ClipboardButton,
    Field(discriminator="type"),
]


class InlineKeyboard(BaseModel):
    """A 2D grid of buttons. Limits per Max docs: ≤7 per row, ≤30 rows."""

    model_config = ConfigDict(extra="forbid")

    buttons: list[list[Button]]

    @field_validator("buttons")
    @classmethod
    def _enforce_limits(cls, v: list[list[Button]]) -> list[list[Button]]:
        if len(v) > 30:
            raise ValueError("inline_keyboard: at most 30 rows allowed")
        for i, row in enumerate(v):
            if len(row) == 0:
                raise ValueError(f"inline_keyboard: row {i} is empty")
            if len(row) > 7:
                raise ValueError("inline_keyboard: at most 7 buttons per row")
        return v
