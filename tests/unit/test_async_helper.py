"""async_helperモジュールのユニットテスト"""

import asyncio

import pytest

from wikidot.util.async_helper import run_coroutine


class TestRunCoroutine:
    """run_coroutine関数のテスト"""

    def test_run_simple_coroutine(self) -> None:
        """単純なコルーチンを実行できる"""

        async def simple_coro() -> int:
            return 42

        result: int = run_coroutine(simple_coro())
        assert result == 42

    def test_run_coroutine_with_await(self) -> None:
        """awaitを含むコルーチンを実行できる"""

        async def coro_with_await() -> str:
            await asyncio.sleep(0.001)
            return "completed"

        result: str = run_coroutine(coro_with_await())
        assert result == "completed"

    def test_run_coroutine_preserves_return_value_dict(self) -> None:
        """辞書の戻り値が正しく保持される"""

        async def return_dict() -> dict[str, int]:
            return {"key": 123, "another": 456}

        result: dict[str, int] = run_coroutine(return_dict())
        assert result == {"key": 123, "another": 456}

    def test_run_coroutine_preserves_return_value_list(self) -> None:
        """リストの戻り値が正しく保持される"""

        async def return_list() -> list[int]:
            return [1, 2, 3]

        result: list[int] = run_coroutine(return_list())
        assert result == [1, 2, 3]

    def test_run_coroutine_propagates_exception(self) -> None:
        """例外が正しく伝播される"""

        async def raise_error() -> None:
            raise ValueError("test error message")

        with pytest.raises(ValueError, match="test error message"):
            run_coroutine(raise_error())

    def test_run_coroutine_propagates_custom_exception(self) -> None:
        """カスタム例外が正しく伝播される"""

        class CustomError(Exception):
            pass

        async def raise_custom_error() -> None:
            raise CustomError("custom error")

        with pytest.raises(CustomError, match="custom error"):
            run_coroutine(raise_custom_error())

    def test_run_coroutine_in_existing_loop(self) -> None:
        """既存のイベントループ内でも動作する"""

        async def outer() -> int:
            async def inner() -> int:
                return 42

            return run_coroutine(inner())

        result = asyncio.run(outer())
        assert result == 42

    def test_run_coroutine_in_existing_loop_propagates_exception(self) -> None:
        """既存ループ内でも例外が正しく伝播される"""

        async def outer() -> None:
            async def raise_error() -> None:
                raise ValueError("nested error")

            run_coroutine(raise_error())

        with pytest.raises(ValueError, match="nested error"):
            asyncio.run(outer())

    def test_run_coroutine_with_gather(self) -> None:
        """asyncio.gatherを含むコルーチンを実行できる"""

        async def multiple_tasks() -> list[int]:
            async def task(n: int) -> int:
                return n * 2

            results = await asyncio.gather(task(1), task(2), task(3))
            return list(results)

        result: list[int] = run_coroutine(multiple_tasks())
        assert result == [2, 4, 6]

    def test_run_coroutine_none_return(self) -> None:
        """Noneを返すコルーチンを実行できる"""

        async def return_none() -> None:
            pass

        result: None = run_coroutine(return_none())
        assert result is None
