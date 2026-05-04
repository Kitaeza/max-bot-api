"""Retry policy and backoff calculation.

RetryPolicy is configuration; the loop that uses it lives in transport.py.
Both the dataclass and the _backoff helper are kept here so the policy
math has one home and one test file.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """Opt-in retry policy for MaxClient.

    Attributes:
        max_attempts: Total attempts including the first. 1 disables retry.
        backoff_initial: Seconds to wait before the second attempt.
        backoff_multiplier: Each subsequent wait is multiplied by this.
        backoff_max: Cap on a single wait, in seconds.
        jitter: If True, multiply each wait by a uniform [0.75, 1.25] factor
            to prevent thundering-herd retries.
    """

    max_attempts: int = 3
    backoff_initial: float = 1.0
    backoff_multiplier: float = 2.0
    backoff_max: float = 30.0
    jitter: bool = True


def _backoff(policy: RetryPolicy, attempt: int) -> float:
    """Seconds to wait before retry number `attempt + 1`.

    `attempt` is 1-indexed: pass the number of the attempt that just failed.
    """
    base = min(
        policy.backoff_initial * (policy.backoff_multiplier ** (attempt - 1)),
        policy.backoff_max,
    )
    if policy.jitter:
        return base * random.uniform(0.75, 1.25)
    return base
