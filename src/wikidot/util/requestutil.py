import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from wikidot.module.client import Client


class RequestUtil:
    @staticmethod
    def request(
        client: "Client", method: str, urls: list[str], return_exceptions: bool = False
    ) -> list[httpx.Response | Exception]:
        """GETリクエストを送信する

        Parameters
        ----------
        client: Client
            クライアント
        method: str
            リクエストメソッド
        urls: list[str]
            URLのリスト
        return_exceptions: bool
            例外を返すかどうか (True: 返す, False: 例外を送出)
            デフォルトでは例外を送出

        Returns
        -------
        list[httpx.Response | Exception]
            レスポンスのリスト
        """
        config = client.amc_client.config
        semaphore = asyncio.Semaphore(config.semaphore_limit)

        async def _get(url: str) -> httpx.Response:
            async with semaphore:
                async with httpx.AsyncClient() as _client:
                    return await _client.get(url)

        async def _post(url: str) -> httpx.Response:
            async with semaphore:
                async with httpx.AsyncClient() as _client:
                    return await _client.post(url)

        async def _execute():
            if method == "GET":
                return await asyncio.gather(*[_get(url) for url in urls], return_exceptions=return_exceptions)
            elif method == "POST":
                return await asyncio.gather(*[_post(url) for url in urls], return_exceptions=return_exceptions)
            else:
                raise ValueError("Invalid method")

        def _run_async(coro):
            """Execute an async coroutine in the current or new event loop"""
            try:
                # Get the running event loop
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop exists, create a new one and run
                return asyncio.run(coro)
            else:
                # Run in a separate thread to avoid conflict with the existing loop
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()

        return _run_async(_execute())
