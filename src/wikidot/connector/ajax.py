"""
Module responsible for communication with Wikidot's Ajax Module Connector

This module provides classes and utilities for communicating with
Wikidot site's ajax-module-connector.php. It features async communication,
error handling, and retry functionality.
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
from ..util.http import sync_get_with_retry


class AjaxRequestHeader:
    """
    Class for managing request headers used in Ajax Module Connector communication

    Manages Content-Type, User-Agent, Referer, Cookie, etc.,
    and provides functionality to generate appropriate HTTP headers.
    """

    def __init__(
        self,
        content_type: str | None = None,
        user_agent: str | None = None,
        referer: str | None = None,
        cookie: dict | None = None,
    ):
        """
        Initialize AjaxRequestHeader

        Parameters
        ----------
        content_type : str | None, default None
            Content-Type to set. Default value is used if None
        user_agent : str | None, default None
            User-Agent to set. Default value is used if None
        referer : str | None, default None
            Referer to set. Default value is used if None
        cookie : dict | None, default None
            Cookie to set. Empty dict is used if None
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
        Set a cookie

        Parameters
        ----------
        name : str
            Name of the cookie to set
        value : str
            Value of the cookie to set
        """
        self.cookie[name] = value
        return

    def delete_cookie(self, name: str) -> None:
        """
        Delete a cookie

        Parameters
        ----------
        name : str
            Name of the cookie to delete
        """
        del self.cookie[name]
        return

    def get_header(self) -> dict:
        """
        Get the constructed HTTP headers

        Returns
        -------
        dict
            Header dictionary for HTTP requests
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
    Data class holding Ajax Module Connector communication settings

    Manages settings such as request timeout, retry count, and concurrent connections.

    Attributes
    ----------
    request_timeout : int, default 20
        Request timeout in seconds
    attempt_limit : int, default 3
        Maximum number of retries on error
    retry_interval : float, default 1.0
        Base retry interval in seconds. Used as the basis for exponential backoff
    max_backoff : float, default 60.0
        Maximum retry interval in seconds
    backoff_factor : float, default 2.0
        Exponential backoff factor (interval is multiplied by this factor for each retry)
    semaphore_limit : int, default 10
        Maximum number of concurrent async requests
    """

    request_timeout: int = 20
    attempt_limit: int = 5
    retry_interval: float = 1.0
    max_backoff: float = 60.0
    backoff_factor: float = 2.0
    semaphore_limit: int = 10


def _mask_sensitive_data(body: dict[str, Any]) -> dict[str, Any]:
    """
    Mask sensitive information for log output

    Parameters
    ----------
    body : dict[str, Any]
        Request body to mask

    Returns
    -------
    dict[str, Any]
        Dictionary with sensitive information masked
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
    Calculate exponential backoff interval (with jitter)

    Parameters
    ----------
    retry_count : int
        Current retry count (starting from 1)
    base_interval : float
        Base interval in seconds
    backoff_factor : float
        Backoff factor (interval is multiplied by this factor for each retry)
    max_backoff : float
        Maximum backoff interval in seconds

    Returns
    -------
    float
        Calculated backoff interval in seconds
    """
    # backoff_factor^(retry_count-1) * base_interval
    backoff = (backoff_factor ** (retry_count - 1)) * base_interval
    # Add 10% jitter
    jitter = random.uniform(0, backoff * 0.1)
    return min(backoff + jitter, max_backoff)


class AjaxModuleConnectorClient:
    """
    Client class for communicating with Wikidot's Ajax Module Connector

    Performs HTTP requests to ajax-module-connector.php and processes responses.
    Features async communication, retry processing, and error handling.
    """

    def __init__(
        self,
        site_name: str | None = None,
        config: AjaxModuleConnectorConfig | None = None,
    ):
        """
        Initialize AjaxModuleConnectorClient

        Parameters
        ----------
        site_name : str | None, default None
            Wikidot site name to connect to. "www" is used if None
        config : AjaxModuleConnectorConfig | None, default None
            Communication settings. Default values are used if None
        """
        self.site_name: str = site_name if site_name is not None else "www"
        self.config: AjaxModuleConnectorConfig = config if config is not None else AjaxModuleConnectorConfig()

        # Check SSL support
        self.ssl_supported: bool = self._check_existence_and_ssl()

        # Initialize headers
        self.header: AjaxRequestHeader = AjaxRequestHeader()

    def _check_existence_and_ssl(self) -> bool:
        """
        Check site existence and SSL support status

        Sends an actual HTTP request to verify site existence and
        determines SSL support status by checking if redirected to HTTPS.

        Returns
        -------
        bool
            True if the site supports SSL, False otherwise

        Raises
        ------
        NotFoundException
            If the specified site does not exist
        """
        # www always supports SSL
        if self.site_name == "www":
            return True

        # For other sites, determine by checking if redirected to https
        response = sync_get_with_retry(
            f"http://{self.site_name}.wikidot.com",
            timeout=self.config.request_timeout,
            attempt_limit=self.config.attempt_limit,
            retry_interval=self.config.retry_interval,
            max_backoff=self.config.max_backoff,
            backoff_factor=self.config.backoff_factor,
            follow_redirects=False,
            raise_for_status=False,
        )

        # Raise exception if not found
        if response.status_code == httpx.codes.NOT_FOUND:
            raise NotFoundException(f"Site is not found: {self.site_name}.wikidot.com")

        # Determine by checking if redirected to https
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
        Send request to Ajax Module Connector and get response

        Processes multiple requests asynchronously in parallel and automatically retries on error.

        Parameters
        ----------
        bodies : list[dict[str, Any]]
            List of request bodies to send
        return_exceptions : bool, default False
            Whether to return or raise exceptions (True: return, False: raise)
        site_name : str | None, default None
            Target site name. Uses the site name specified at initialization if None
        site_ssl_supported : bool | None, default None
            Site's SSL support status. Uses the result confirmed at initialization if None

        Returns
        -------
        tuple[httpx.Response, ...] | tuple[httpx.Response | Exception, ...]
            Tuple of responses or exceptions (in same order as requests)

        Raises
        ------
        AMCHttpStatusCodeException
            If HTTP status code is not 200 (when return_exceptions is False)
        WikidotStatusCodeException
            If response status is not "ok" (when return_exceptions is False)
        ResponseDataException
            If response is invalid JSON format or empty (when return_exceptions is False)
        """
        semaphore_instance = asyncio.Semaphore(self.config.semaphore_limit)

        site_name = site_name if site_name is not None else self.site_name
        site_ssl_supported = site_ssl_supported if site_ssl_supported is not None else self.ssl_supported

        async def _request(_body: dict[str, Any]) -> httpx.Response:
            retry_count = 0
            response: httpx.Response | None = None

            while True:
                # Execute request
                try:
                    # Control concurrent execution with Semaphore
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
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    # Retry on all request errors (HTTP errors, timeouts, network errors, etc.)
                    # Wikidot server has a relatively high error rate, so retry is essential
                    retry_count += 1

                    # Raise exception if retry limit reached
                    if retry_count >= self.config.attempt_limit:
                        error_detail = str(response.status_code) if response is not None else str(e)
                        wd_logger.error(f"AMC request failed: {error_detail} -> {_mask_sensitive_data(_body)}")
                        raise AMCHttpStatusCodeException(
                            f"AMC request failed: {error_detail}",
                            response.status_code if response is not None else 999,
                        ) from e

                    # Retry with exponential backoff interval
                    backoff = _calculate_backoff(
                        retry_count,
                        self.config.retry_interval,
                        self.config.backoff_factor,
                        self.config.max_backoff,
                    )
                    error_info = str(response.status_code) if response is not None else str(e)
                    wd_logger.info(
                        f"AMC request error: {error_info} "
                        f"(retry: {retry_count}, backoff: {backoff:.2f}s) -> {_mask_sensitive_data(_body)}"
                    )
                    await asyncio.sleep(backoff)
                    continue

                # Parse body as JSON data
                try:
                    _response_body = response.json()
                except json.decoder.JSONDecodeError:
                    # Retry on JSON parse error (e.g., empty response)
                    retry_count += 1
                    if retry_count >= self.config.attempt_limit:
                        wd_logger.error(
                            f'AMC is respond non-json data: "{response.text}" -> {_mask_sensitive_data(_body)}'
                        )
                        raise ResponseDataException(f'AMC is respond non-json data: "{response.text}"') from None

                    backoff = _calculate_backoff(
                        retry_count,
                        self.config.retry_interval,
                        self.config.backoff_factor,
                        self.config.max_backoff,
                    )
                    wd_logger.info(f"AMC responded with non-JSON data (retry: {retry_count}, backoff: {backoff:.2f}s)")
                    await asyncio.sleep(backoff)
                    continue

                # Retry if response is empty
                if _response_body is None or len(_response_body) == 0:
                    retry_count += 1
                    if retry_count >= self.config.attempt_limit:
                        wd_logger.error(f"AMC is respond empty data -> {_mask_sensitive_data(_body)}")
                        raise ResponseDataException("AMC is respond empty data")

                    backoff = _calculate_backoff(
                        retry_count,
                        self.config.retry_interval,
                        self.config.backoff_factor,
                        self.config.max_backoff,
                    )
                    wd_logger.info(f"AMC responded with empty data (retry: {retry_count}, backoff: {backoff:.2f}s)")
                    await asyncio.sleep(backoff)
                    continue

                # Treat as error if status is not ok
                if "status" in _response_body:
                    # Retry if status is try_again
                    if _response_body["status"] == "try_again":
                        retry_count += 1
                        if retry_count >= self.config.attempt_limit:
                            wd_logger.error(f'AMC is respond status: "try_again" -> {_mask_sensitive_data(_body)}')
                            raise WikidotStatusCodeException('AMC is respond status: "try_again"', "try_again")

                        # Retry with exponential backoff interval
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

                    # Treat as error if status is not ok for other cases
                    elif _response_body["status"] != "ok":
                        wd_logger.error(
                            f'AMC is respond error status: "{_response_body["status"]}" -> '
                            f"{_mask_sensitive_data(_body)}"
                        )
                        raise WikidotStatusCodeException(
                            f'AMC is respond error status: "{_response_body["status"]}"',
                            _response_body["status"],
                        )

                # Return response
                return response

        async def _execute_requests() -> list[httpx.Response | BaseException]:
            return await asyncio.gather(
                *[_request(body) for body in bodies],
                return_exceptions=return_exceptions,
            )

        # Execute processing (works safely even in existing loop environments)
        results: list[httpx.Response | BaseException] = run_coroutine(_execute_requests())
        return tuple(
            r if isinstance(r, httpx.Response) else r if isinstance(r, Exception) else Exception(str(r))
            for r in results
        )
