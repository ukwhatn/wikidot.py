from typing import TYPE_CHECKING

import httpx

from wikidot.common.exceptions import SessionCreateException

if TYPE_CHECKING:
    from wikidot.module.client import Client


class HTTPAuthentication:
    @staticmethod
    def login(
        client: "Client",
        username: str,
        password: str,
    ):
        """ユーザー名とパスワードでログインする

        Parameters
        ----------
        client: Client
            クライアント
        username: str
            ユーザー名
        password: str
            パスワード
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
                "Login attempt is failed due to HTTP status code: "
                + str(response.status_code)
            )

        # Check body
        if "The login and password do not match" in response.text:
            raise SessionCreateException(
                "Login attempt is failed due to invalid username or password"
            )

        # Check cookies
        if "WIKIDOT_SESSION_ID" not in response.cookies:
            raise SessionCreateException(
                "Login attempt is failed due to invalid cookies"
            )

        # Set cookies
        client.amc_client.header.set_cookie(
            "WIKIDOT_SESSION_ID", response.cookies["WIKIDOT_SESSION_ID"]
        )

    @staticmethod
    def logout(client: "Client"):
        try:
            client.amc_client.request(
                [{"action": "Login2Action", "event": "logout", "moduleName": "Empty"}]
            )
        except Exception:
            pass

        client.amc_client.header.delete_cookie("WIKIDOT_SESSION_ID")
