from typing import TYPE_CHECKING

import httpx

from ..common.exceptions import SessionCreateException

if TYPE_CHECKING:
    from .client import Client


class HTTPAuthentication:
    """
    WikidotへのHTTP認証を提供するクラス

    ログインおよびログアウト処理を管理するための静的メソッドを提供する。
    """

    @staticmethod
    def login(
        client: "Client",
        username: str,
        password: str,
    ):
        """
        ユーザー名とパスワードでWikidotにログインする

        Parameters
        ----------
        client : Client
            接続するクライアントインスタンス
        username : str
            ログインするユーザー名
        password : str
            ユーザーのパスワード

        Raises
        ------
        SessionCreateException
            ログイン試行が失敗した場合（HTTP応答コードエラー、認証情報不一致、Cookieの問題等）
        """
        # ログインリクエスト実行
        response = httpx.post(
            url="https://www.wikidot.com/default--flow/login__LoginPopupScreen",
            data={
                "login": username,
                "password": password,
                "action": "Login2Action",
                "event": "login",
            },
            headers=client.amc_client.header.get_header(),
            timeout=20,
        )

        # Check status code
        if response.status_code != httpx.codes.OK:
            raise SessionCreateException(
                "Login attempt is failed due to HTTP status code: " + str(response.status_code)
            )

        # Check body
        if "The login and password do not match" in response.text:
            raise SessionCreateException("Login attempt is failed due to invalid username or password")

        # Check cookies
        if "WIKIDOT_SESSION_ID" not in response.cookies:
            raise SessionCreateException("Login attempt is failed due to invalid cookies")

        # Set cookies
        client.amc_client.header.set_cookie("WIKIDOT_SESSION_ID", response.cookies["WIKIDOT_SESSION_ID"])

    @staticmethod
    def logout(client: "Client"):
        """
        Wikidotからログアウトする

        Parameters
        ----------
        client : Client
            ログアウトするクライアントインスタンス

        Notes
        -----
        ログアウト処理でエラーが発生しても無視され、Cookieの削除は常に行われる。
        """
        try:
            client.amc_client.request([{"action": "Login2Action", "event": "logout", "moduleName": "Empty"}])
        except Exception:
            pass

        client.amc_client.header.delete_cookie("WIKIDOT_SESSION_ID")
