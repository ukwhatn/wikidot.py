import asyncio
from typing import TYPE_CHECKING

import httpx

from .async_helper import run_coroutine

if TYPE_CHECKING:
    from wikidot.module.client import Client


class RequestUtil:
    @staticmethod
    def request(
        client: "Client", method: str, urls: list[str], return_exceptions: bool = False
    ) -> list[httpx.Response | Exception]:
        """Send GET request

        Parameters
        ----------
        client: Client
            Client instance
        method: str
            Request method
        urls: list[str]
            List of URLs
        return_exceptions: bool
            Whether to return exceptions (True: return, False: raise)
            Default is to raise exceptions

        Returns
        -------
        list[httpx.Response | Exception]
            List of responses
        """
        config = client.amc_client.config
        semaphore = asyncio.Semaphore(config.semaphore_limit)

        async def _get(url: str) -> httpx.Response:
            async with semaphore, httpx.AsyncClient() as _client:
                return await _client.get(url)

        async def _post(url: str) -> httpx.Response:
            async with semaphore, httpx.AsyncClient() as _client:
                return await _client.post(url)

        async def _execute() -> list[httpx.Response | BaseException]:
            if method == "GET":
                return await asyncio.gather(*[_get(url) for url in urls], return_exceptions=return_exceptions)
            elif method == "POST":
                return await asyncio.gather(*[_post(url) for url in urls], return_exceptions=return_exceptions)
            else:
                raise ValueError("Invalid method")

        results: list[httpx.Response | BaseException] = run_coroutine(_execute())
        return [
            r if isinstance(r, httpx.Response) else r if isinstance(r, Exception) else Exception(str(r))
            for r in results
        ]
