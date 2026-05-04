import httpx
import respx

from max_bot_api import MaxClient
from max_bot_api.models.attachments import (
    AudioAttachment,
    FileAttachment,
    ImageAttachment,
    VideoAttachment,
)

_BASE = "https://platform-api.max.ru"
_UPLOAD_URL = "https://uploads.max.ru/u/abc"


def _mock_upload(media_type: str) -> None:
    respx.post(f"{_BASE}/uploads", params={"type": media_type}).mock(
        return_value=httpx.Response(200, json={"url": _UPLOAD_URL})
    )
    respx.post(_UPLOAD_URL).mock(return_value=httpx.Response(200, json={"token": "tok-xyz"}))


@respx.mock
async def test_upload_image() -> None:
    _mock_upload("image")
    async with MaxClient(token="t", base_url=_BASE) as c:
        att = await c.upload_image(b"image-bytes", filename="pic.jpg")
    assert isinstance(att, ImageAttachment)
    assert att.payload.token == "tok-xyz"


@respx.mock
async def test_upload_video() -> None:
    _mock_upload("video")
    async with MaxClient(token="t", base_url=_BASE) as c:
        att = await c.upload_video(b"video-bytes", filename="vid.mp4")
    assert isinstance(att, VideoAttachment)


@respx.mock
async def test_upload_audio() -> None:
    _mock_upload("audio")
    async with MaxClient(token="t", base_url=_BASE) as c:
        att = await c.upload_audio(b"audio-bytes")
    assert isinstance(att, AudioAttachment)


@respx.mock
async def test_upload_file_attachment() -> None:
    _mock_upload("file")
    async with MaxClient(token="t", base_url=_BASE) as c:
        att = await c.upload_file_attachment(b"file-bytes", filename="doc.pdf")
    assert isinstance(att, FileAttachment)


@respx.mock
async def test_upload_image_default_content_type_omitted() -> None:
    """No explicit content_type → upload_file uses application/octet-stream
    fallback (the upload host then sniffs from bytes)."""
    _mock_upload("image")
    async with MaxClient(token="t", base_url=_BASE) as c:
        await c.upload_image(b"png-bytes", filename="pic.png")
    # The actual upload request body should have application/octet-stream
    upload_request = respx.calls.last.request
    body = upload_request.read()
    assert b"application/octet-stream" in body


@respx.mock
async def test_upload_image_explicit_content_type() -> None:
    """Explicit content_type flows through to the upload request."""
    _mock_upload("image")
    async with MaxClient(token="t", base_url=_BASE) as c:
        await c.upload_image(b"png-bytes", filename="pic.png", content_type="image/png")
    upload_request = respx.calls.last.request
    body = upload_request.read()
    assert b"image/png" in body
