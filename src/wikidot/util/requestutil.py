import asyncio
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

        return asyncio.run(_execute())
