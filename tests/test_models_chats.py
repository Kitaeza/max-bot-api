from max_bot_api.models.chats import Chat, ChatType


def test_chat_type_enum() -> None:
    assert ChatType.DIALOG.value == "dialog"
    assert ChatType.CHAT.value == "chat"
    assert ChatType.CHANNEL.value == "channel"


def test_chat_round_trip() -> None:
    payload = {
        "chat_id": 42,
        "type": "channel",
        "status": "active",
        "title": "My Channel",
        "icon": None,
        "last_event_time": 1234567890,
        "participants_count": 5,
        "is_public": True,
        "link": "https://max.ru/channel",
        "description": "Test channel",
        "owner_id": 1,
    }
    chat = Chat.model_validate(payload)
    assert chat.chat_id == 42
    assert chat.type == ChatType.CHANNEL
    assert chat.title == "My Channel"


def test_chat_ignores_unknown_fields() -> None:
    payload = {
        "chat_id": 42,
        "type": "chat",
        "status": "active",
        "last_event_time": 0,
        "future_field": "ignored",
    }
    chat = Chat.model_validate(payload)
    assert chat.chat_id == 42
