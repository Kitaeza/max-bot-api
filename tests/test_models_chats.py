from max_bot_api.models.chats import (
    Chat,
    ChatAction,
    ChatAdminPermission,
    ChatMember,
    ChatMemberList,
    ChatType,
)


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


def test_chat_admin_permission_enum_values() -> None:
    assert ChatAdminPermission.READ_ALL_MESSAGES.value == "read_all_messages"
    assert ChatAdminPermission.WRITE.value == "write"
    assert ChatAdminPermission.DELETE_MESSAGE.value == "delete_message"
    assert len(list(ChatAdminPermission)) == 11


def test_chat_action_enum_values() -> None:
    assert ChatAction.TYPING_ON.value == "typing_on"
    assert ChatAction.SENDING_PHOTO.value == "sending_photo"
    assert ChatAction.SENDING_VIDEO.value == "sending_video"
    assert ChatAction.SENDING_AUDIO.value == "sending_audio"
    assert ChatAction.SENDING_FILE.value == "sending_file"
    assert len(list(ChatAction)) == 5


def test_chat_member_round_trip_full() -> None:
    payload = {
        "user_id": 100,
        "first_name": "Alice",
        "last_name": "Admin",
        "username": "alice",
        "is_bot": False,
        "last_activity_time": 1700000000000,
        "description": "test user",
        "avatar_url": "https://cdn/a.png",
        "full_avatar_url": "https://cdn/a-full.png",
        "last_access_time": 1700000001000,
        "join_time": 1600000000000,
        "is_owner": True,
        "is_admin": True,
        "alias": "Boss",
        "permissions": ["write", "pin_message", "delete_message"],
    }
    m = ChatMember.model_validate(payload)
    assert m.user_id == 100
    assert m.is_owner is True
    assert m.permissions == [
        ChatAdminPermission.WRITE,
        ChatAdminPermission.PIN_MESSAGE,
        ChatAdminPermission.DELETE_MESSAGE,
    ]


def test_chat_member_round_trip_minimal() -> None:
    """Non-admin member without chat-specific extras."""
    payload = {
        "user_id": 200,
        "first_name": "Bob",
        "is_bot": False,
        "last_activity_time": 1700000000000,
    }
    m = ChatMember.model_validate(payload)
    assert m.user_id == 200
    assert m.last_name is None
    assert m.permissions is None
    assert m.is_admin is None


def test_chat_member_ignores_unknown_fields() -> None:
    payload = {
        "user_id": 1,
        "first_name": "X",
        "is_bot": False,
        "last_activity_time": 0,
        "future_field": "ignored",
    }
    m = ChatMember.model_validate(payload)
    assert m.user_id == 1


def test_chat_member_list_round_trip_with_marker() -> None:
    payload = {
        "members": [
            {
                "user_id": 1,
                "first_name": "A",
                "is_bot": False,
                "last_activity_time": 0,
            }
        ],
        "marker": 12345,
    }
    page = ChatMemberList.model_validate(payload)
    assert len(page.members) == 1
    assert page.marker == 12345


def test_chat_member_list_marker_can_be_null() -> None:
    payload: dict[str, object] = {"members": [], "marker": None}
    page = ChatMemberList.model_validate(payload)
    assert page.members == []
    assert page.marker is None
