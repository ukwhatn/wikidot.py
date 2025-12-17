"""非同期実行のヘルパーモジュール

既存のイベントループ環境でも安全に非同期処理を実行するためのユーティリティを提供する。
Jupyter NotebookやFastAPI等、イベントループが既に実行中の環境でも動作する。
"""

import asyncio
import concurrent.futures
from collections.abc import Coroutine
from typing import TypeVar

T = TypeVar("T")


def run_coroutine(coro: Coroutine[None, None, T]) -> T:
    """既存のイベントループ環境でも安全に非同期処理を実行する

    イベントループが既に実行中の場合は別スレッドで実行し、
    そうでない場合は新しいイベントループを作成して実行する。

    Parameters
    ----------
    coro : Coroutine
        実行する非同期コルーチン

    Returns
    -------
    T
        コルーチンの戻り値

    Examples
    --------
    >>> async def example():
    ...     return 42
    >>> result = run_coroutine(example())
    >>> result
    42
    """
    # 既存のイベントループが実行中かチェック
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # 実行中のループがない場合は新しいループを作成
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    else:
        # 実行中のループがある場合は別スレッドで実行
        def _run_in_thread() -> T:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_in_thread)
            return future.result()
