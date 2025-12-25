"""Async execution helper module

Provides utilities for safely executing async operations even in existing event loop environments.
Works in environments where an event loop is already running, such as Jupyter Notebook or FastAPI.
"""

import asyncio
import concurrent.futures
from collections.abc import Coroutine
from typing import TypeVar

T = TypeVar("T")


def run_coroutine(coro: Coroutine[None, None, T]) -> T:
    """Safely execute async operations even in existing event loop environments

    If an event loop is already running, execute in a separate thread.
    Otherwise, create a new event loop and execute.

    Parameters
    ----------
    coro : Coroutine
        Async coroutine to execute

    Returns
    -------
    T
        Return value of the coroutine

    Examples
    --------
    >>> async def example():
    ...     return 42
    >>> result = run_coroutine(example())
    >>> result
    42
    """
    # Check if an existing event loop is running
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # If no running loop, create a new loop
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    else:
        # If there is a running loop, execute in a separate thread
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
