from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from max_bot_api.models.attachments import (
    Attachment,
    AttachmentType,
    AudioAttachment,
    FileAttachment,
    ImageAttachment,
    InlineKeyboardAttachment,
    VideoAttachment,
)
from max_bot_api.models.keyboards import (
    CallbackButton,
    InlineKeyboard,
    LinkButton,
)

_ADAPTER: TypeAdapter[Any] = TypeAdapter(Attachment)


def test_image_attachment_round_trip() -> None:
    payload = {"type": "image", "payload": {"token": "abc", "url": "https://x/y.jpg"}}
    parsed = _ADAPTER.validate_python(payload)
    assert isinstance(parsed, ImageAttachment)
    assert parsed.payload.token == "abc"
    assert _ADAPTER.dump_python(parsed) == payload


def test_video_attachment_round_trip() -> None:
    payload = {"type": "video", "payload": {"token": "v1"}}
    parsed = _ADAPTER.validate_python(payload)
    assert isinstance(parsed, VideoAttachment)
    assert parsed.payload.token == "v1"


def test_audio_attachment_round_trip() -> None:
    payload = {"type": "audio", "payload": {"token": "a1"}}
    parsed = _ADAPTER.validate_python(payload)
    assert isinstance(parsed, AudioAttachment)


def test_file_attachment_round_trip() -> None:
    payload = {"type": "file", "payload": {"token": "f1"}}
    parsed = _ADAPTER.validate_python(payload)
    assert isinstance(parsed, FileAttachment)


def test_inline_keyboard_attachment_round_trip() -> None:
    payload = {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [{"type": "link", "text": "Open", "url": "https://example.com"}],
                [{"type": "callback", "text": "Hi", "payload": "x"}],
            ],
        },
    }
    parsed = _ADAPTER.validate_python(payload)
    assert isinstance(parsed, InlineKeyboardAttachment)
    assert isinstance(parsed.payload.buttons[0][0], LinkButton)
    assert isinstance(parsed.payload.buttons[1][0], CallbackButton)


def test_unknown_attachment_type_raises() -> None:
    with pytest.raises(ValidationError):
        _ADAPTER.validate_python({"type": "telepathy", "payload": {}})


def test_attachment_type_enum_covers_all() -> None:
    assert AttachmentType.IMAGE.value == "image"
    assert AttachmentType.VIDEO.value == "video"
    assert AttachmentType.AUDIO.value == "audio"
    assert AttachmentType.FILE.value == "file"
    assert AttachmentType.INLINE_KEYBOARD.value == "inline_keyboard"


def test_inline_keyboard_validates_button_count() -> None:
    # Max docs: ≤ 7 link buttons per row, ≤ 30 rows total
    too_many_per_row: list[Any] = [
        {"type": "link", "text": str(i), "url": "https://x"} for i in range(8)
    ]
    with pytest.raises(ValidationError):
        InlineKeyboard(buttons=[too_many_per_row])

    too_many_rows: list[Any] = [
        [{"type": "callback", "text": "x", "payload": "p"}] for _ in range(31)
    ]
    with pytest.raises(ValidationError):
        InlineKeyboard(buttons=too_many_rows)
