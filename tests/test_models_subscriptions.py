from max_bot_api.models.subscriptions import Subscription


def test_subscription_round_trip() -> None:
    payload = {
        "url": "https://example.com/webhook",
        "time": 1700000000000,
        "update_types": ["message_created", "bot_started"],
    }
    sub = Subscription.model_validate(payload)
    assert sub.url == "https://example.com/webhook"
    assert sub.time == 1700000000000
    assert sub.update_types == ["message_created", "bot_started"]


def test_subscription_update_types_optional() -> None:
    payload = {"url": "https://example.com/webhook", "time": 1700000000000}
    sub = Subscription.model_validate(payload)
    assert sub.update_types is None


def test_subscription_tolerates_unknown_update_type_strings() -> None:
    """Server may add new update types; the response model uses raw strings
    so a future-compatible value never crashes the client."""
    payload = {
        "url": "https://example.com/webhook",
        "time": 1700000000000,
        "update_types": ["message_created", "future_event_type_2030"],
    }
    sub = Subscription.model_validate(payload)
    assert "future_event_type_2030" in (sub.update_types or [])


def test_subscription_ignores_unknown_fields() -> None:
    payload = {
        "url": "https://example.com/webhook",
        "time": 0,
        "future_field": "ignored",
    }
    sub = Subscription.model_validate(payload)
    assert sub.url == "https://example.com/webhook"
