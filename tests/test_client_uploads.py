import httpx
import respx

from max_bot_api import MaxClient
from max_bot_api.models.uploads import UploadEndpoint, UploadResult

_BASE = "https://platform-api.max.ru"
_UPLOAD_URL = "https://uploads.max.ru/u/abc"


@respx.mock
async def test_request_upload_url_image() -> None:
    route = respx.post(f"{_BASE}/uploads", params={"type": "image"}).mock(
        return_value=httpx.Response(200, json={"url": _UPLOAD_URL})
    )
    async with MaxClient(token="t", base_url=_BASE) as c:
        endpoint = await c.request_upload_url(type="image")
    assert isinstance(endpoint, UploadEndpoint)
    assert endpoint.url == _UPLOAD_URL
    assert route.called


@respx.mock
async def test_upload_file_posts_bytes_and_returns_token() -> None:
    respx.post(_UPLOAD_URL).mock(return_value=httpx.Response(200, json={"token": "tok-xyz"}))
    async with MaxClient(token="t", base_url=_BASE) as c:
        result = await c.upload_file(
            _UPLOAD_URL, b"hello", filename="hi.txt", content_type="text/plain"
        )
    assert isinstance(result, UploadResult)
    assert result.token == "tok-xyz"


@respx.mock
async def test_upload_file_sends_multipart_with_filename() -> None:
    route = respx.post(_UPLOAD_URL).mock(return_value=httpx.Response(200, json={"token": "tok"}))
    async with MaxClient(token="t", base_url=_BASE) as c:
        await c.upload_file(_UPLOAD_URL, b"data", filename="photo.jpg", content_type="image/jpeg")
    body = route.calls.last.request.read()
    # multipart body contains the filename and content-type
    assert b'filename="photo.jpg"' in body
    assert b"image/jpeg" in body
