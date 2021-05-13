# -*- coding: utf-8 -*-

""""wikidot.connector

send HTTP Request to wikidot.com/ajax-module-connector.php

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""

import httpx
import asyncio
import html

from . import variables, exceptions, logger


async def connect(*, url: str, body: dict, unescape: bool = True, attempt_count: int = 10) -> dict:
    """|Coroutine| AMC Request function

    Arguments:
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "www.scpwiki.com"
        body: dict, by default {"wikidot_token7": "123456"}
            HTTP request data
            By default, wikidot_token7 is inserted (common with the header), so please insert any other required values.
        unescape: bool, by default True
            whether to unescape value returns
        attempt_count: int, by default 3
            How many times to retry if the request fails

    Raises:
        wikidot.exceptions.StatusIsNotOKError(msg, status_code)
            The status returned by Wikidot was not OK
        wikidot.exceptions.RequestFailedError(msg, html_response_code)
            Function tried the request several times but it failed.

    Returns:
        dict
            Dictionary converted from JSON returned by Wikidot
    """
    # Requester
    async def _innerfunc(url, data, headers):
        async with httpx.AsyncClient() as client:
            try:
                _r = await client.post(
                    f"http://{url}/ajax-module-connector.php/",
                    data=_request_body,
                    headers=variables.request_header,
                    timeout=60.0
                )
            except Exception:
                raise exceptions.RequestFailedError(
                    "Unexpected Error occurred while requesting", "request_error"
                )
        # Check statuscode
        if _r.status_code != 200:
            raise exceptions.RequestFailedError(
                "Status code is not 200.", _r.status_code
            )
        # json decode
        try:
            _json = _r.json()
        except Exception:
            raise exceptions.ReturnedDataError(
                "Returned data is not json format.", "not_json"
            )
        if _json is None:
            raise exceptions.ReturnedDataError(
                "Wikidot returns empty data.", "empty"
            )

        logger.logger.info(
            f"AMC | POSTED {url} | {data['moduleName'] if data['moduleName'] != 'Empty' else data['action']} | {_json['status']}"
        )

        return _json

    # Create HTTP Request Body
    _request_body = {
        "wikidot_token7": "123456"
    }

    _request_body.update(body)

    # Request
    _json = {}
    _st = False
    _cnt = 0
    while _st is False:
        try:
            _json = await _innerfunc(url=url, headers=variables.request_header, data=_request_body)
            r_status = _json["status"]
            if r_status == "try_again":
                raise
            _st = True
        except Exception as e:
            if _cnt < attempt_count:
                logger.logger.warning(
                    f"AMC | Failed, try again after 10sec... | {e.args[1]}"
                )
                _cnt += 1
                await asyncio.sleep(10.0)
                pass
            else:
                logger.logger.error(
                    "AMC | Attempts have reached the limit",
                    exc_info=True
                )
                raise exceptions.RequestFailedError(
                    "Request attempted but failed.", "attempt_out"
                )

    # Wikidot Errors
    if r_status != "ok":
        raise exceptions.StatusIsNotOKError(
            "Status is not OK", r_status
        )

    if "body" in _json and unescape is True:
        _json["body"] = html.unescape(_json["body"])

    return _json
