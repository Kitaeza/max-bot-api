"""Upload-related response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UploadEndpoint(BaseModel):
    """Response from POST /uploads — where to PUT/POST the file bytes."""

    model_config = ConfigDict(extra="ignore")

    url: str
    token: str | None = None  # not always returned at request time


class UploadResult(BaseModel):
    """Response from the upload destination after the file is sent."""

    model_config = ConfigDict(extra="ignore")

    token: str
