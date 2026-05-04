import pytest
from pydantic import ValidationError

from max_bot_api.models.messages import (
    Message,
    MessageRecipient,
    MessageSender,
    MessageStat,
    NewMessageBody,
    NewMessageLink,
    TextFormat,
)

# Smoke-check that nested types are importable and constructible
_SENDER = MessageSender(user_id=0, name="bot")
_RECIPIENT = MessageRecipient(chat_type="dialog")


def test_text_format_values() -> None:
    assert TextFormat.HTML.value == "html"
    assert TextFormat.MARKDOWN.value == "markdown"


def test_new_message_body_minimal() -> None:
    body = NewMessageBody(text="hi")
    assert body.text == "hi"
    assert body.notify is True
    assert body.format is None


def test_new_message_body_dump_drops_unset_optional_fields() -> None:
    body = NewMessageBody(text="hi")
    dumped = body.model_dump(exclude_none=True, by_alias=True)
    assert dumped == {"text": "hi", "notify": True}


def test_new_message_body_with_format_serializes_value() -> None:
    body = NewMessageBody(text="**hi**", format=TextFormat.MARKDOWN)
    dumped = body.model_dump(exclude_none=True, by_alias=True)
    assert dumped["format"] == "markdown"


def test_new_message_body_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        NewMessageBody(text="hi", bogus="nope")  # type: ignore[call-arg]


def test_new_message_link_minimal() -> None:
    link = NewMessageLink(type="reply", mid="abc123")
    assert link.type == "reply"
    assert link.mid == "abc123"


def test_message_round_trip() -> None:
    payload = {
        "sender": {
            "user_id": 1, "name": "Alice", "username": "alice",
            "is_bot": False, "last_activity_time": 0
        },
        "recipient": {"chat_id": 42, "chat_type": "chat", "user_id": None},
        "timestamp": 1234567890,
        "link": None,
        "body": {"mid": "m1", "seq": 1, "text": "hi", "attachments": []},
        "stat": None,
        "url": None,
    }
    msg = Message.model_validate(payload)
    assert msg.body.mid == "m1"
    assert msg.body.text == "hi"
    assert msg.recipient.chat_id == 42
    # Round-trip preserves the structure
    dumped = msg.model_dump(by_alias=True, exclude_none=False)
    assert dumped["body"]["mid"] == "m1"


def test_message_ignores_unknown_response_fields() -> None:
    payload = {
        "sender": {
            "user_id": 1, "name": "Alice", "username": "alice",
            "is_bot": False, "last_activity_time": 0
        },
        "recipient": {"chat_id": 42, "chat_type": "chat", "user_id": None},
        "timestamp": 1234567890,
        "body": {"mid": "m1", "seq": 1, "text": "hi", "attachments": []},
        "future_field": "ignored",  # Max may add fields; we must not crash
    }
    msg = Message.model_validate(payload)
    assert msg.body.text == "hi"


def test_message_stat() -> None:
    stat = MessageStat(views=100)
    assert stat.views == 100
