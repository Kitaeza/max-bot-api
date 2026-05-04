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
