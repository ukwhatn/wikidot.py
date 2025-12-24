"""リトライ付き検証ヘルパー

Wikidot APIのeventual consistencyを考慮し、
期待する条件が満たされるまでリトライを行うためのヘルパー
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def wait_for_condition(
    fn: Callable[[], T],
    predicate: Callable[[T], bool],
    max_retries: int = 10,
    interval: float = 2.0,
) -> T:
    """条件が満たされるまでリトライする

    Args:
        fn: 値を取得する関数
        predicate: 条件を判定する関数
        max_retries: 最大リトライ回数（デフォルト: 10）
        interval: リトライ間隔（秒、デフォルト: 2.0）

    Returns:
        条件を満たした値

    Raises:
        TimeoutError: 条件を満たさないままリトライ上限に達した場合
    """
    for _ in range(max_retries):
        time.sleep(interval)
        value = fn()
        if predicate(value):
            return value
    raise TimeoutError(f"Condition not met after {max_retries} retries")
