from max_bot_api.models.bot import BotCommand, BotInfo


def test_bot_command_round_trip() -> None:
    payload = {"name": "start", "description": "Begin"}
    cmd = BotCommand.model_validate(payload)
    assert cmd.name == "start"
    assert cmd.description == "Begin"


def test_bot_command_description_optional() -> None:
    cmd = BotCommand.model_validate({"name": "ping"})
    assert cmd.description is None


def test_bot_info_round_trip_full() -> None:
    payload = {
        "user_id": 999,
        "first_name": "TestBot",
        "last_name": None,
        "username": "test_bot",
        "is_bot": True,
        "last_activity_time": 1700000000000,
        "name": "TestBot",
        "description": "A test bot",
        "avatar_url": "https://cdn/avatar.png",
        "full_avatar_url": "https://cdn/avatar-full.png",
        "commands": [
            {"name": "start", "description": "Begin"},
            {"name": "help"},
        ],
    }
    me = BotInfo.model_validate(payload)
    assert me.user_id == 999
    assert me.is_bot is True
    assert me.commands is not None
    assert len(me.commands) == 2
    assert me.commands[0].name == "start"
    assert me.commands[1].description is None


def test_bot_info_round_trip_minimal() -> None:
    payload = {
        "user_id": 1,
        "first_name": "Bot",
        "is_bot": True,
        "last_activity_time": 0,
    }
    me = BotInfo.model_validate(payload)
    assert me.username is None
    assert me.commands is None


def test_bot_info_ignores_unknown_fields() -> None:
    payload = {
        "user_id": 1,
        "first_name": "Bot",
        "is_bot": True,
        "last_activity_time": 0,
        "future_field": "ignored",
    }
    me = BotInfo.model_validate(payload)
    assert me.user_id == 1
