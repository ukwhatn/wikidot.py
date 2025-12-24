"""
WikidotのAjax Module Connectorとの通信を担当するモジュール

このモジュールは、Wikidotサイトのajax-module-connector.phpとの通信を行うための
クラスやユーティリティを提供する。非同期通信、エラーハンドリング、リトライ機能を備えている。
"""

import asyncio
import json.decoder
import random
from dataclasses import dataclass
from typing import Any, Literal, overload

import httpx

from ..common import wd_logger
from ..common.exceptions import (
    AMCHttpStatusCodeException,
    ForbiddenException,
    NotFoundException,
    ResponseDataException,
    WikidotStatusCodeException,
)
from ..util.async_helper import run_coroutine


class AjaxRequestHeader:
    """
    Ajax Module Connector通信時に使用するリクエストヘッダを管理するクラス

    Content-Type、User-Agent、Referer、Cookieなどを管理し、
    適切なHTTPヘッダを生成する機能を提供する。
    """

    def __init__(
        self,
        content_type: str | None = None,
        user_agent: str | None = None,
        referer: str | None = None,
        cookie: dict | None = None,
    ):
        """
        AjaxRequestHeaderの初期化

        Parameters
        ----------
        content_type : str | None, default None
            設定するContent-Type。Noneの場合はデフォルト値が使用される
        user_agent : str | None, default None
            設定するUser-Agent。Noneの場合はデフォルト値が使用される
        referer : str | None, default None
            設定するReferer。Noneの場合はデフォルト値が使用される
        cookie : dict | None, default None
            設定するCookie。Noneの場合は空の辞書が使用される
        """
        self.content_type: str = (
            "application/x-www-form-urlencoded; charset=UTF-8" if content_type is None else content_type
        )
        self.user_agent: str = "WikidotPy" if user_agent is None else user_agent
        self.referer: str = "https://www.wikidot.com/" if referer is None else referer
        self.cookie: dict[str, Any] = {"wikidot_token7": 123456}
        if cookie is not None:
            self.cookie.update(cookie)
        return

    def set_cookie(self, name: str, value: Any) -> None:
        """
        Cookieを設定する

        Parameters
        ----------
        name : str
            設定するCookieの名前
        value : str
            設定するCookieの値
        """
        self.cookie[name] = value
        return

    def delete_cookie(self, name: str) -> None:
        """
        Cookieを削除する

        Parameters
        ----------
        name : str
            削除するCookieの名前
        """
        del self.cookie[name]
        return

    def get_header(self) -> dict:
        """
        構築されたHTTPヘッダを取得する

        Returns
        -------
        dict
            HTTPリクエスト用のヘッダ辞書
        """
        return {
            "Content-Type": self.content_type,
            "User-Agent": self.user_agent,
            "Referer": self.referer,
            "Cookie": "".join([f"{name}={value};" for name, value in self.cookie.items()]),
        }


@dataclass
class AjaxModuleConnectorConfig:
    """
    Ajax Module Connector通信の設定を保持するデータクラス

    リクエストのタイムアウト、リトライ回数、並行通信数などの
    設定を管理する。

    Attributes
    ----------
    request_timeout : int, default 20
        リクエストのタイムアウト秒数
    attempt_limit : int, default 3
        エラー発生時のリトライ上限回数
    retry_interval : float, default 1.0
        リトライの基本間隔（秒）。指数バックオフの基準値
    max_backoff : float, default 60.0
        リトライ間隔の最大値（秒）
    backoff_factor : float, default 2.0
        指数バックオフの係数（各リトライごとに間隔がこの係数倍される）
    semaphore_limit : int, default 10
        非同期リクエストの最大並行数
    """

    request_timeout: int = 20
    attempt_limit: int = 5
    retry_interval: float = 1.0
    max_backoff: float = 60.0
    backoff_factor: float = 2.0
    semaphore_limit: int = 10


def _mask_sensitive_data(body: dict[str, Any]) -> dict[str, Any]:
    """
    ログ出力用に機密情報をマスクする

    Parameters
    ----------
    body : dict[str, Any]
        マスク対象のリクエストボディ

    Returns
    -------
    dict[str, Any]
        機密情報がマスクされた辞書
    """
    masked = body.copy()
    sensitive_keys = {"password", "login", "WIKIDOT_SESSION_ID", "wikidot_token7"}
    for key in sensitive_keys:
        if key in masked:
            masked[key] = "***MASKED***"
    return masked


def _calculate_backoff(
    retry_count: int,
    base_interval: float,
    backoff_factor: float,
    max_backoff: float,
) -> float:
    """
    指数バックオフ間隔を計算する（ジッター付き）

    Parameters
    ----------
    retry_count : int
        現在のリトライ回数（1から開始）
    base_interval : float
        基本間隔（秒）
    backoff_factor : float
        バックオフ係数（各リトライごとに間隔がこの係数倍される）
    max_backoff : float
        最大バックオフ間隔（秒）

    Returns
    -------
    float
        計算されたバックオフ間隔（秒）
    """
    # backoff_factor^(retry_count-1) * base_interval
    backoff = (backoff_factor ** (retry_count - 1)) * base_interval
    # 10%のジッターを追加
    jitter = random.uniform(0, backoff * 0.1)
    return min(backoff + jitter, max_backoff)


class AjaxModuleConnectorClient:
    """
    WikidotのAjax Module Connectorと通信するクライアントクラス

    ajax-module-connector.phpへのHTTPリクエストを行い、レスポンスを処理する。
    非同期通信、リトライ処理、エラーハンドリングなどの機能を備えている。
    """

    def __init__(
        self,
        site_name: str | None = None,
        config: AjaxModuleConnectorConfig | None = None,
    ):
        """
        AjaxModuleConnectorClientの初期化

        Parameters
        ----------
        site_name : str | None, default None
            接続先のWikidotサイト名。Noneの場合は"www"が使用される
        config : AjaxModuleConnectorConfig | None, default None
            通信設定。Noneの場合はデフォルト値が使用される
        """
        self.site_name: str = site_name if site_name is not None else "www"
        self.config: AjaxModuleConnectorConfig = config if config is not None else AjaxModuleConnectorConfig()

        # ssl対応チェック
        self.ssl_supported: bool = self._check_existence_and_ssl()

        # ヘッダの初期化
        self.header: AjaxRequestHeader = AjaxRequestHeader()

    def _check_existence_and_ssl(self) -> bool:
        """
        サイトの存在とSSL対応状況を確認する

        実際にHTTPリクエストを送信し、サイトの存在を確認するとともに、
        HTTPSにリダイレクトされるかどうかでSSL対応状況を判断する。

        Returns
        -------
        bool
            サイトがSSL対応している場合はTrue、そうでない場合はFalse

        Raises
        ------
        NotFoundException
            指定されたサイトが存在しない場合
        """
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

    @overload
    def request(
        self,
        bodies: list[dict[str, Any]],
        return_exceptions: Literal[False] = False,
        site_name: str | None = None,
        site_ssl_supported: bool | None = None,
    ) -> tuple[httpx.Response, ...]: ...

    @overload
    def request(
        self,
        bodies: list[dict[str, Any]],
        return_exceptions: Literal[True],
        site_name: str | None = None,
        site_ssl_supported: bool | None = None,
    ) -> tuple[httpx.Response | Exception, ...]: ...

    def request(
        self,
        bodies: list[dict[str, Any]],
        return_exceptions: bool = False,
        site_name: str | None = None,
        site_ssl_supported: bool | None = None,
    ) -> tuple[httpx.Response, ...] | tuple[httpx.Response | Exception, ...]:
        """
        Ajax Module Connectorにリクエストを送信し、レスポンスを取得する

        複数のリクエストを非同期で並行処理し、エラー発生時には自動的にリトライを行う。

        Parameters
        ----------
        bodies : list[dict[str, Any]]
            送信するリクエストボディのリスト
        return_exceptions : bool, default False
            例外を返すか送出するか (True: 返す, False: 送出する)
        site_name : str | None, default None
            接続先サイト名。Noneの場合は初期化時に指定したサイト名が使用される
        site_ssl_supported : bool | None, default None
            サイトのSSL対応状況。Noneの場合は初期化時に確認した結果が使用される

        Returns
        -------
        tuple[httpx.Response, ...] | tuple[httpx.Response | Exception, ...]
            レスポンスまたは例外のタプル（リクエストと同じ順序）

        Raises
        ------
        AMCHttpStatusCodeException
            HTTPステータスコードが200以外の場合（return_exceptionsがFalseの場合）
        WikidotStatusCodeException
            レスポンスのステータスが"ok"でない場合（return_exceptionsがFalseの場合）
        ResponseDataException
            レスポンスが不正なJSON形式または空の場合（return_exceptionsがFalseの場合）
        """
        semaphore_instance = asyncio.Semaphore(self.config.semaphore_limit)

        site_name = site_name if site_name is not None else self.site_name
        site_ssl_supported = site_ssl_supported if site_ssl_supported is not None else self.ssl_supported

        async def _request(_body: dict[str, Any]) -> httpx.Response:
            retry_count = 0
            response: httpx.Response | None = None

            while True:
                # リクエスト実行
                try:
                    # Semaphoreで同時実行数制御
                    async with semaphore_instance, httpx.AsyncClient() as client:
                        url = (
                            f"http{'s' if site_ssl_supported else ''}://{site_name}.wikidot.com/"
                            f"ajax-module-connector.php"
                        )
                        _body["wikidot_token7"] = 123456
                        wd_logger.debug(f"Ajax Request: {url} -> {_mask_sensitive_data(_body)}")
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
                            f"AMC is respond HTTP error code: "
                            f"{response.status_code if response is not None else 'timeout'} -> "
                            f"{_mask_sensitive_data(_body)}"
                        )
                        raise AMCHttpStatusCodeException(
                            f"AMC is respond HTTP error code: "
                            f"{response.status_code if response is not None else 'timeout'}",
                            response.status_code if response is not None else 999,
                        ) from e

                    # 指数バックオフで間隔を空けてリトライ
                    backoff = _calculate_backoff(
                        retry_count,
                        self.config.retry_interval,
                        self.config.backoff_factor,
                        self.config.max_backoff,
                    )
                    wd_logger.info(
                        f"AMC is respond status: {response.status_code if response is not None else 'timeout'} "
                        f"(retry: {retry_count}, backoff: {backoff:.2f}s) -> {_mask_sensitive_data(_body)}"
                    )
                    await asyncio.sleep(backoff)
                    continue

                # bodyをJSONデータとしてパース
                try:
                    _response_body = response.json()
                except json.decoder.JSONDecodeError as e:
                    # パースできなかったらエラーとして扱う
                    wd_logger.error(f'AMC is respond non-json data: "{response.text}" -> {_mask_sensitive_data(_body)}')
                    raise ResponseDataException(f'AMC is respond non-json data: "{response.text}"') from e

                # レスポンスが空だったらエラーとして扱う
                if _response_body is None or len(_response_body) == 0:
                    wd_logger.error(f"AMC is respond empty data -> {_mask_sensitive_data(_body)}")
                    raise ResponseDataException("AMC is respond empty data")

                # 中身のstatusがokでなかったらエラーとして扱う
                if "status" in _response_body:
                    # statusがtry_againの場合はリトライ
                    if _response_body["status"] == "try_again":
                        retry_count += 1
                        if retry_count >= self.config.attempt_limit:
                            wd_logger.error(f'AMC is respond status: "try_again" -> {_mask_sensitive_data(_body)}')
                            raise WikidotStatusCodeException('AMC is respond status: "try_again"', "try_again")

                        # 指数バックオフで間隔を空けてリトライ
                        backoff = _calculate_backoff(
                            retry_count,
                            self.config.retry_interval,
                            self.config.backoff_factor,
                            self.config.max_backoff,
                        )
                        wd_logger.info(
                            f'AMC is respond status: "try_again" (retry: {retry_count}, backoff: {backoff:.2f}s)'
                        )
                        await asyncio.sleep(backoff)
                        continue

                    elif _response_body["status"] == "no_permission":
                        target_str = "unknown"
                        if "moduleName" in _body:
                            target_str = f"moduleName: {_body['moduleName']}"
                        elif "action" in _body:
                            target_str = f"action: {_body['action']}/{_body['event'] if 'event' in _body else ''}"
                        raise ForbiddenException(f"Your account has no permission to perform this action: {target_str}")

                    # それ以外でstatusがokでない場合はエラーとして扱う
                    elif _response_body["status"] != "ok":
                        wd_logger.error(
                            f'AMC is respond error status: "{_response_body["status"]}" -> '
                            f"{_mask_sensitive_data(_body)}"
                        )
                        raise WikidotStatusCodeException(
                            f'AMC is respond error status: "{_response_body["status"]}"',
                            _response_body["status"],
                        )

                # レスポンスを返す
                return response

        async def _execute_requests() -> list[httpx.Response | BaseException]:
            return await asyncio.gather(
                *[_request(body) for body in bodies],
                return_exceptions=return_exceptions,
            )

        # 処理を実行（既存のループがある環境でも安全に動作）
        results: list[httpx.Response | BaseException] = run_coroutine(_execute_requests())
        return tuple(
            r if isinstance(r, httpx.Response) else r if isinstance(r, Exception) else Exception(str(r))
            for r in results
        )
