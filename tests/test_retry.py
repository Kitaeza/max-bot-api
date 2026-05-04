"""Tests for RetryPolicy and _backoff."""

import dataclasses
import math

import pytest

from max_bot_api.retry import RetryPolicy, _backoff


def test_retry_policy_defaults_match_spec() -> None:
    p = RetryPolicy()
    assert p.max_attempts == 3
    assert p.backoff_initial == 1.0
    assert p.backoff_multiplier == 2.0
    assert p.backoff_max == 30.0
    assert p.jitter is True


def test_retry_policy_is_frozen() -> None:
    p = RetryPolicy()
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.max_attempts = 99  # type: ignore[misc]


def test_backoff_no_jitter_matches_documented_sequence() -> None:
    p = RetryPolicy(jitter=False)
    # Wait BEFORE attempt N+1 — i.e., after attempt N failed.
    assert _backoff(p, 1) == 1.0
    assert _backoff(p, 2) == 2.0
    assert _backoff(p, 3) == 4.0


def test_backoff_saturates_at_backoff_max() -> None:
    p = RetryPolicy(backoff_initial=10.0, backoff_multiplier=10.0, backoff_max=30.0, jitter=False)
    assert _backoff(p, 1) == 10.0
    assert _backoff(p, 2) == 30.0  # 100 capped to 30
    assert _backoff(p, 3) == 30.0  # 1000 capped to 30


def test_backoff_jitter_stays_within_25_percent_band() -> None:
    p = RetryPolicy(jitter=True)
    base = 4.0  # _backoff(p, 3) without jitter
    samples = [_backoff(p, 3) for _ in range(500)]
    assert all(0.75 * base <= s <= 1.25 * base for s in samples)
    # Sanity: jitter actually varies (not all identical)
    assert len({round(s, 6) for s in samples}) > 10


def test_backoff_jitter_off_is_deterministic() -> None:
    p = RetryPolicy(jitter=False)
    assert math.isclose(_backoff(p, 2), _backoff(p, 2))
