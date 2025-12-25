import contextlib
from typing import TYPE_CHECKING

import httpx

from ..common.exceptions import SessionCreateException

if TYPE_CHECKING:
    from .client import Client


class HTTPAuthentication:
    """
    Class that provides HTTP authentication for Wikidot

    Provides static methods for managing login and logout processing.
    """

    @staticmethod
    def login(
        client: "Client",
        username: str,
        password: str,
    ) -> None:
        """
        Log in to Wikidot with username and password

        Parameters
        ----------
        client : Client
            The client instance to connect
        username : str
            The username to log in with
        password : str
            The user's password

        Raises
        ------
        SessionCreateException
            If the login attempt fails (HTTP response code error, credential mismatch, cookie issues, etc.)
        """
        # Execute login request
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
    def logout(client: "Client") -> None:
        """
        Log out from Wikidot

        Parameters
        ----------
        client : Client
            The client instance to log out

        Notes
        -----
        Errors during the logout process are ignored, and cookie deletion is always performed.
        """
        with contextlib.suppress(Exception):
            client.amc_client.request([{"action": "Login2Action", "event": "logout", "moduleName": "Empty"}])

        client.amc_client.header.delete_cookie("WIKIDOT_SESSION_ID")
