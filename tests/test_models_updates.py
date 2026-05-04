import pytest
from pydantic import TypeAdapter, ValidationError

from max_bot_api.models.updates import (
    BotStartedUpdate,
    MessageCreatedUpdate,
    MessageEditedUpdate,
    MessageRemovedUpdate,
    Update,
    UpdateList,
    UpdateType,
)

_ADAPTER: TypeAdapter[Update] = TypeAdapter(Update)


def test_update_type_enum() -> None:
    assert UpdateType.MESSAGE_CREATED.value == "message_created"
    assert UpdateType.MESSAGE_EDITED.value == "message_edited"
    assert UpdateType.MESSAGE_REMOVED.value == "message_removed"
    assert UpdateType.BOT_STARTED.value == "bot_started"


def test_message_created_update() -> None:
    payload = {
        "update_type": "message_created",
        "timestamp": 1234567890,
        "message": {
            "sender": {"user_id": 1, "name": "Alice"},
            "recipient": {"chat_id": 42, "chat_type": "chat"},
            "timestamp": 1234567890,
            "body": {"mid": "m1", "seq": 1, "text": "hi", "attachments": []},
        },
    }
    parsed = _ADAPTER.validate_python(payload)
    assert isinstance(parsed, MessageCreatedUpdate)
    assert parsed.message.body.text == "hi"


def test_message_edited_update() -> None:
    payload = {
        "update_type": "message_edited",
        "timestamp": 1234567890,
        "message": {
            "sender": {"user_id": 1, "name": "Alice"},
            "recipient": {"chat_id": 42, "chat_type": "chat"},
            "timestamp": 1234567890,
            "body": {"mid": "m1", "seq": 2, "text": "edited", "attachments": []},
        },
    }
    parsed = _ADAPTER.validate_python(payload)
    assert isinstance(parsed, MessageEditedUpdate)


def test_message_removed_update() -> None:
    payload = {
        "update_type": "message_removed",
        "timestamp": 1234567890,
        "message_id": "m1",
        "chat_id": 42,
        "user_id": 1,
    }
    parsed = _ADAPTER.validate_python(payload)
    assert isinstance(parsed, MessageRemovedUpdate)
    assert parsed.message_id == "m1"


def test_bot_started_update() -> None:
    payload = {
        "update_type": "bot_started",
        "timestamp": 1234567890,
        "chat_id": 42,
        "user": {"user_id": 1, "name": "Alice"},
    }
    parsed = _ADAPTER.validate_python(payload)
    assert isinstance(parsed, BotStartedUpdate)


def test_unknown_update_type_raises() -> None:
    with pytest.raises(ValidationError):
        _ADAPTER.validate_python({"update_type": "telepathy", "timestamp": 0})


def test_update_list_carries_marker() -> None:
    payload = {
        "updates": [
            {
                "update_type": "message_removed",
                "timestamp": 1234567890,
                "message_id": "m1",
                "chat_id": 42,
                "user_id": 1,
            }
        ],
        "marker": 99,
    }
    ul = UpdateList.model_validate(payload)
    assert ul.marker == 99
    assert len(ul.updates) == 1
    assert isinstance(ul.updates[0], MessageRemovedUpdate)


def test_update_list_empty() -> None:
    ul = UpdateList(updates=[], marker=None)
    assert ul.updates == []
    assert ul.marker is None
