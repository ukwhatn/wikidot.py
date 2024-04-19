import asyncio
import json.decoder
from dataclasses import dataclass
from typing import Any

import httpx

from ..common import wd_logger
from ..common.exceptions import (
    AMCHttpStatusCodeException,
    NotFoundException,
    ResponseDataException,
    WikidotStatusCodeException,
)


class AjaxRequestHeader:
    """ajax-module-connector.phpへのリクエスト時に利用するヘッダの構築用クラス"""

    def __init__(
        self,
        content_type: str | None = None,
        user_agent: str | None = None,
        referer: str | None = None,
        cookie: dict | None = None,
    ):
        """AjaxRequestHeaderオブジェクトの初期化

        Parameters
        ----------
        content_type: str | None
            Content-Type
        user_agent: str | None
            User-Agent
        referer: str | None
            Referer
        cookie: dict | None
            Cookie
        """
        self.content_type: str = (
            "application/x-www-form-urlencoded; charset=UTF-8"
            if content_type is None
            else content_type
        )
        self.user_agent: str = "WikidotPy" if user_agent is None else user_agent
        self.referer: str = "https://www.wikidot.com/" if referer is None else referer
        self.cookie: dict[str, Any] = {"wikidot_token7": 123456}
        if cookie is not None:
            self.cookie.update(cookie)
        return

    def set_cookie(self, name, value) -> None:
        """Cookieを設定する

        Parameters
        ----------
        name: str
            Cookie名
        value: str
            Cookie値
        """
        self.cookie[name] = value
        return

    def delete_cookie(self, name) -> None:
        """Cookieを削除する

        Parameters
        ----------
        name: str
            Cookie名
        """
        del self.cookie[name]
        return

    def get_header(self) -> dict:
        """ヘッダを構築して返す

        Returns
        -------
        dict
            ヘッダ
        """
        return {
            "Content-Type": self.content_type,
            "User-Agent": self.user_agent,
            "Referer": self.referer,
            "Cookie": "".join(
                [f"{name}={value};" for name, value in self.cookie.items()]
            ),
        }


@dataclass
class AjaxModuleConnectorConfig:
    """ajax-module-connector.phpへのリクエストを行う際の設定

    Attributes
    ----------
    request_timeout: int
        タイムアウト
    attempt_limit: int
        リクエストの試行回数上限
    retry_interval: int
        リクエスト失敗時のリトライ間隔
    semaphore_limit: int
        セマフォの上限
    """

    request_timeout: int = 20
    attempt_limit: int = 3
    retry_interval: int = 5
    semaphore_limit: int = 10


class AjaxModuleConnectorClient:
    """ajax-module-connector.phpへのリクエストを行うクライアント"""

    def __init__(
        self,
        site_name: str | None = None,
        config: AjaxModuleConnectorConfig | None = None,
    ):
        """AjaxModuleConnectorClientオブジェクトの初期化

        Parameters
        ----------
        config: AjaxModuleConnectorConfig
            設定
        """
        self.site_name: str = site_name if site_name is not None else "www"
        self.config: AjaxModuleConnectorConfig = (
            config if config is not None else AjaxModuleConnectorConfig()
        )

        # ssl対応チェック
        self.ssl_supported: bool = self._check_existence_and_ssl()

        # ヘッダの初期化
        self.header: AjaxRequestHeader = AjaxRequestHeader()

    def _check_existence_and_ssl(self):
        """実際にアクセスしてみてサイトの存在とSSL対応をチェック"""

        # wwwは常にSSL対応
        if self.site_name == "www":
            return True

        # それ以外のサイトはhttpsにリダイレクトされるかどうかで判断
        response = httpx.get(f"http://{self.site_name}.wikidot.com")

        # 存在しなければ例外送出
        if response.status_code == httpx.codes.NOT_FOUND:
            raise NotFoundException(f"Site is not found: {self.site_name}.wikidot.com")

        # httpsにリダイレクトされているかどうかで判断
        return (
            response.status_code == httpx.codes.MOVED_PERMANENTLY
            and "Location" in response.headers
            and response.headers["Location"].startswith("https")
        )

    def request(
        self,
        bodies: list[dict[str, Any]],
        return_exceptions: bool = False,
        site_name: str | None = None,
        site_ssl_supported: bool | None = None,
    ) -> tuple[BaseException | Any]:
        """ajax-module-connector.phpへのリクエストを行う

        Parameters
        ----------
        bodies: list[dict]
            リクエストボディのリスト
        return_exceptions: bool
            例外を返すかどうか (True: 返す, False: 例外を送出)
            デフォルトでは例外を送出
        site_name: str | None
            サイト名
            デフォルトでは初期化時に指定したサイト名
        site_ssl_supported: bool | None
            サイトがSSL対応しているかどうか
            デフォルトでは初期化時にチェックした結果

        Returns
        -------
        dict
            レスポンスボディのリスト（順序はリクエストボディのリストと同じ）

        Raises
        ------
        AMCHttpStatusCodeException
            AMCから返却されたHTTPステータスが200以外だったときの例外

        WikidotStatusCodeException
            AMCから返却されたデータ内のステータスがokではなかったときの例外
            HTTPステータスが200以外の場合はAMCHttpStatusCodeExceptionを投げる

        ResponseDataException
            AMCから返却されたデータが不正だったときの例外
            JSONデータとしてパースできなかった場合や空だった場合に投げる
        """
        semaphore_instance = asyncio.Semaphore(self.config.semaphore_limit)

        site_name = site_name if site_name is not None else self.site_name
        site_ssl_supported = (
            site_ssl_supported if site_ssl_supported is not None else self.ssl_supported
        )

        async def _request(_body: dict[str, Any]) -> httpx.Response:
            retry_count = 0

            while True:

                # リクエスト実行
                try:
                    # Semaphoreで同時実行数制御
                    async with semaphore_instance:
                        async with httpx.AsyncClient() as client:
                            url = (
                                f'http{"s" if site_ssl_supported else ""}://{site_name}.wikidot.com/'
                                f"ajax-module-connector.php"
                            )
                            _body["wikidot_token7"] = 123456
                            wd_logger.debug(f"Ajax Request: {url} -> {_body}")
                            response = await client.post(
                                url,
                                headers=self.header.get_header(),
                                data=_body,
                                timeout=self.config.request_timeout,
                            )
                            response.raise_for_status()
                except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
                    # HTTPステータスエラーまたはタイムアウトの場合はリトライ
                    retry_count += 1

                    # リトライ回数上限に達した場合は例外送出
                    if retry_count >= self.config.attempt_limit:
                        wd_logger.error(
                            f"AMC is respond HTTP error code: {response.status_code} -> {_body}"
                        )
                        raise AMCHttpStatusCodeException(
                            f"AMC is respond HTTP error code: {response.status_code}",
                            response.status_code,
                        ) from e

                    # 間隔を空けてリトライ
                    wd_logger.info(
                        f"AMC is respond status: {response.status_code} (retry: {retry_count}) -> {_body}"
                    )
                    await asyncio.sleep(self.config.retry_interval)
                    continue

                # bodyをJSONデータとしてパース
                try:
                    _response_body = response.json()
                except json.decoder.JSONDecodeError as e:
                    # パースできなかったらエラーとして扱う
                    wd_logger.error(
                        f'AMC is respond non-json data: "{response.text}" -> {_body}'
                    )
                    raise ResponseDataException(
                        f'AMC is respond non-json data: "{response.text}"'
                    ) from e

                # レスポンスが空だったらエラーとして扱う
                if _response_body is None or len(_response_body) == 0:
                    wd_logger.error(f"AMC is respond empty data -> {_body}")
                    raise ResponseDataException("AMC is respond empty data")

                # 中身のstatusがokでなかったらエラーとして扱う
                if "status" in _response_body:
                    # statusがtry_againの場合はリトライ
                    if _response_body["status"] == "try_again":
                        retry_count += 1
                        if retry_count >= self.config.attempt_limit:
                            wd_logger.error(
                                f'AMC is respond status: "try_again" -> {_body}'
                            )
                            raise WikidotStatusCodeException(
                                'AMC is respond status: "try_again"', "try_again"
                            )

                        wd_logger.info(
                            f'AMC is respond status: "try_again" (retry: {retry_count})'
                        )
                        await asyncio.sleep(self.config.retry_interval)
                        continue

                    # それ以外でstatusがokでない場合はエラーとして扱う
                    elif _response_body["status"] != "ok":
                        wd_logger.error(
                            f'AMC is respond error status: "{_response_body["status"]}" -> {_body}'
                        )
                        raise WikidotStatusCodeException(
                            f'AMC is respond error status: "{_response_body["status"]}"',
                            _response_body["status"],
                        )

                # レスポンスを返す
                return response

        async def _execute_requests():
            return await asyncio.gather(
                *[_request(body) for body in bodies],
                return_exceptions=return_exceptions,
            )

        # 処理を実行
        return asyncio.run(_execute_requests())
