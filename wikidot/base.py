# -*- coding: utf-8 -*-

"""wikidot.base

Basement functions for wikidot.py

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""

from . import connector, decorator, exceptions, logger, variables

import asyncio
from bs4 import BeautifulSoup as bs4
import httpx
import feedparser

import math
from typing import Union, Optional
from datetime import datetime
from time import mktime
import re


logger = logger.logger

# --------------------
# BASE PARSERS
# --------------------


def author_parser(printuserelement):
    if "class" in printuserelement.attrs and "deleted" in printuserelement["class"]:
        author_name = "account deleted"
        author_unix = "account_deleted"
        author_id = int(printuserelement["data-id"])
    elif "class" in printuserelement.attrs and "anonymous" in printuserelement["class"]:
        author_name = "Anonymous"
        author_unix = printuserelement.find("span", class_="ip").get_text().replace("(", "").replace(")", "").strip()
        author_id = None
    elif len(printuserelement.find_all("a", recursive=False)) == 1:
        author_name = printuserelement.get_text()
        author_unix = author_name.replace("-", "_").replace(" ", "_").lower()
        author_id = None
    elif printuserelement.get_text() == "Wikidot":
        author_name = "Wikidot"
        author_unix = "wikidot"
        author_id = None
    else:
        _author = printuserelement.find_all("a")[1]
        author_name = _author.get_text()
        author_unix = str(_author["href"]).replace("http://www.wikidot.com/user:info/", "")
        author_id = int(
            str(_author["onclick"]).replace("WIKIDOT.page.listeners.userInfo(", "").replace("); return false;", "")
        )
    return author_name, author_unix, author_id


def odate_parser(odateelement):
    _odate_classes = odateelement["class"]
    for _odate_class in _odate_classes:
        if "time_" in str(_odate_class):
            unixtime = int(str(_odate_class).replace("time_", ""))
            return datetime.fromtimestamp(unixtime)


# --------------------
# SessionControl
# --------------------


async def user_login(*, user: str, password: str) -> bool:
    """|Coroutine| Create session on wikidot

    Arguments:
        user: str
            Wikidot account username
        password: str
            Wikidot account password

    Raises:
        wikidot.exceptions.SessionCreateError(msg, reason)
            reason:
                "create_error":
                    HTTP error occurred while requesting for login
                "check_error":
                    Wikidot returns "no_permission" when session checked.
        wikidot.exceptions.UnexpectedError(msg, reason)
            reason:
                "undefined":
                    Error occurred while checking session, and it is not expected.
                [status_wikidot_returns]:
                    Wikidot returned status is neither "ok" nor "no_permission".

    Returns:
        bool
            Return True when creating session is successful.
    """
    """
    Memo:
        1. httpxライブラリを用いてブラウザからwikidotにログインする際と同じリクエストを送信
        2. レスポンスに含まれるクッキー情報からセッションIDを取得
        3. vairables.request_headerとvariables.sessionidに格納
        このとき、ユーザー名やパスの間違いでログインできていなくてもsessionidは発行されるため、エラーにならない
        ログインできていないことを検知するため、以下の操作を行う
        4. dashboard/settings/DSAccountModuleにAMCリクエスト
        5. status:no_permissionが返ってこない(=connector.connectがNoAvailableSessionErrorをraiseしない)ことを確認
        6. ここまで通ればTrueをreturn
    """
    # Login
    try:
        _login = httpx.post(
            url="https://www.wikidot.com/default--flow/login__LoginPopupScreen",
            data={
                "login": user,
                "password": password,
                "action": "Login2Action",
                "event": "login"
            },
            timeout=20
        )

        variables.sessionid = _login.cookies["WIKIDOT_SESSION_ID"]
        variables.username = user
        variables.request_header = {
            "Cookie": f"wikidot_token7=123456;WIKIDOT_SESSION_ID={variables.sessionid};",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        }
        logger.info(
            f"Login | user: {user}"
        )

    except Exception:
        raise exceptions.SessionCreateError(
            "Failed to create session.", "create_error"
        )

    # Check
    try:
        await connector.connect(
            url="www.wikidot.com",
            body={
                "moduleName": "dashboard/settings/DSAccountModule",
                "wikidot_token7": "123456"
            }
        )

    except exceptions.StatusIsNotOKError as e:
        if e[1] == "no_permission":
            logger.error(
                "Login | Session is not available."
            )
            raise exceptions.SessionCreateError(
                "Error occured while checking session", "check_error"
            )
        else:
            raise exceptions.UnexpectedError(
                "Unexpected values is returned by Wikidot while checking session.", e[1]
            )

    except Exception:
        raise exceptions.UnexpectedError(
            "Unexpected Error occurred while checking session.", "undefined"
        )

    variables.logged_in = True

    return True


@decorator.require_session
async def user_logout() -> bool:
    """|AMC| |Coroutine| |SessionRequired| Logout from wikidot

    Arguments:
        None

    Raises:
        None

    Returns:
        bool
            whether logout is successful
    """
    """
    MEMO:
        1. Login2ActionをAMCリクエスト
        2. variablesの各変数に格納されていたセッション情報を削除
        3. Trueを返す
        ここまで、主にconnector.connect()がエラーをraiseしたらFalseを返す

        大抵関数の最後に使われるであろう関数であるため、エラーをraiseしないようにしている
        （Errorレベルでlog出力しているので、把握は可能）
    """
    try:
        await connector.connect(
            url="scp-jp.wikidot.com",
            body={
                "wikidot_token7": "123456",
                "action": "Login2Action",
                "event": "logout",
                "moduleName": "Empty"
            }
        )
        logger.info(
            f"Logout | user: {variables.username}"
        )

        # Delete session info
        variables.logged_in = False
        variables.username = ""
        variables.sessionid = ""
        variables.request_header = {
            "Cookie": "wikidot_token7=123456;",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        }
        logger.info(
            "Logout | Session details are deleted."
        )
        return True
    except Exception:
        logger.error(
            "Logout | Failed to logout from wikidot"
        )
        logger.debug(
            "Logout | Traceback",
            exc_info=True
        )
        return False


async def user_getid(*, user: str) -> int:
    user = user.replace(" ", "-").lstrip("_")
    async with httpx.AsyncClient() as client:
        _source = await client.get(
            f"http://www.wikidot.com/user:info/{user}",
            timeout=10
        )
        if _source.status_code != 200:
            raise

        _contents = bs4(_source.text, 'lxml')
        if len(_contents.select("#page-content .error-block")) != 0:
            return None
        else:
            return int(_contents.select(".profile-title img")[0]["src"].replace("http://www.wikidot.com/avatar.php?userid=", "").split("&")[0])


# --------------------
# LISTPAGES
# --------------------


async def page_getdata(*, url: str, main_key: str = "fullname", module_body: Optional[list[str]] = None, **kwargs) -> Optional[dict]:
    """|AMC| |Coroutine| Get pagedata from ListPages module.

    Arguments:
        url: str
            HTTP Request target url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        main_key: str, by default "fullname"
            main-key of dict returns
            This argument's value need to be in module_body list.
        module_body: list[str], by default
            set acquiring values.
            eg: ["fullname", "created_by"]
            by default:
                [
                    "fullname", "category", "name", "title",
                    "created_at", "created_by_unix", "created_by_id",
                    "updated_at", "updated_by_unix", "updated_by_id",
                    "commented_at", "commented_by_unix", "commented_by_id",
                    "parent_fullname", "comments", "size",
                    "rating_votes", "rating", "revisions", "tags", "_tags"
                ]
        <listpages_module_arguments>: **kwargs
            other arguments that can be given to ListPages Module on wikidot.com
            doc: https://www.wikidot.com/doc-modules:listpages-module
            by default:
                "separate": "no", "wrapper": "no", "perPage": "250",
                "offset": "0", "pagetype": "*", "category": "*"
            Usage:
                >>> wikidot.base.page_getdata(......, category="_default", tags="+scp")

    Raises:
        wikidot.exceptions.ArgumentsError(msg, reason)
            reason:
                "main_key_error":
                    main_key argument value is not in module_body argument values list.
        wikidot.exceptions.StatusIsNotOKError(msg, reason)
            reason:
                [status_wikidot_returns]:
                    Wikidot returned status is not "ok".
                    If the site that you request is private, wikidot returns "not_ok"
        wikidot.exceptions.RequestFailedError(msg, html_response_code)
            AMC Request function tried the request several times but it failed.

    Returns:
        None:
            There is no matching page.
        dict:
            {
                "total": <totalpages>(int)
                <main_key> : {
                    <module_body_value_1>: <value>,
                    <module_body_value_2>: <value>,
                    ....
                }
            }

            If returned value is empty:
                str values:
                    None
                optional int values(created/commented/updated_by_id):
                    None
                not optional int values:
                    0
                datetime values:
                    None

    """
    """
    MEMO:
        ・list/ListPagesModuleにconnector.connectからAMCリクエスト
            -> 返り値をHTMLパース・フォーマットして辞書にする
        ・module_bodyの値は
            <set><n> name </n><v> %%name%% </v></set>
                の形にしてリクエストし、パースを容易にする
    """

    _default_module_body = [
        "fullname",
        "category",
        "name",
        "title",
        "created_at",
        "created_by_unix",
        "created_by_id",
        "updated_at",
        "updated_by_unix",
        "updated_by_id",
        "commented_at",
        "commented_by_unix",
        "commented_by_id",
        "parent_fullname",
        "comments",
        "size",
        "rating_votes",
        "rating",
        "revisions",
        "tags",
        "_tags"
    ]

    if module_body is None:
        module_body = _default_module_body

    if main_key not in module_body:
        raise exceptions.ArgumentsError(
            "main_key is not in module_body.", "main_key_error")

    _body = {
        "moduleName": "list/ListPagesModule",
        "separate": "no",
        "wrapper": "no",
        "perPage": "250",
        "offset": "0",
        "pagetype": "*",
        "category": "*",
        "module_body": "<page>" + "".join(
            map("<set><n> {0} </n><v> %%{0}%% </v></set>".format, module_body)) + "</page>"
    }

    if kwargs is not None:
        # Stringification
        kwargs = {k: str(v) for k, v in kwargs.items()}
        # Merge
        _body.update(kwargs)

    try:
        _r = await connector.connect(
            url=url,
            body=_body
        )
    except exceptions.StatusIsNotOKError as e:
        if e.args[1] == "not_ok":
            logger.warning("Target site may be private.")
        raise
    except exceptions.RequestFailedError:
        raise

    # create dict to result
    _dic_res = {
        "total": 1,  # type: int
        "contents": {}  # type: dict
    }

    # parse
    _r_body = bs4(_r["body"], 'lxml')

    # pager
    pager = _r_body.find("div", class_="pager")
    if pager is not None:
        _dic_res["total"] = int(pager.find_all("span", class_="target")[-2].string)

    # acquire per-page data
    pages = _r_body.find_all("page")

    # when applicable pages is not found
    if not pages:
        logger.info("There is no matching page.")
        return None

    # contain to dict page by page
    for page in pages:

        # FIXME: マシにする
        # FIXME: 5つ星レーティング対応

        # temp-dict to result
        _tmpdic_res = {}

        # search n-s sets
        opts = page.find_all("set")

        # set by set
        for opt in opts:
            name = opt.find("n").string.strip()
            value = opt.find("v")

            # odateではない
            if value.find("span") is None:
                value = str(value.get_text())
                if value is not None:
                    value = value.strip()
                    if value == "":
                        value = None
            # odate
            else:
                value = value.find("span")
                if "_at" not in name:
                    value = str(value.get_text()).strip()

            # datetime
            if "_at" in name:
                if value is not None:
                    _tmpdic_res[name] = odate_parser(value)
                else:
                    _tmpdic_res[name] = value

            # int(not Optional)
            elif name in {"comments", "size", "rating_votes", "rating", "revisions"}:
                if type(value) is not str:
                    value = value.get_text().strip()
                if value is not None:
                    try:
                        _tmpdic_res[name] = int(value)
                    except ValueError:
                        _tmpdic_res[name] = int(float(value))
                else:
                    _tmpdic_res[name] = 0

            # int(Optional)
            elif name in {"created_by_id", "updated_by_id", "commented_by_id"}:
                if value is not None:
                    _tmpdic_res[name] = int(value)
                else:
                    _tmpdic_res[name] = value

            # tuple(tags)
            elif name in {"tags", "_tags"}:
                if value is not None:
                    _tmpdic_res[name] = value.split(" ")
                else:
                    _tmpdic_res[name] = []

            # str
            else:
                _tmpdic_res[name] = str(value) if value is not None else value

        # merge
        _dic_res["contents"].update({_tmpdic_res[main_key]: _tmpdic_res})

    return _dic_res


async def page_getdata_mass(*, limit: int = 10, url: str, main_key: str = "fullname", module_body: Optional[list[str]] = None, **kwargs) -> Optional[dict]:
    """|AMC| |Coroutine| Get all pages' data with base.page_getdata function

    Arguments:
        limit: int, by default 10
            semaphore value = number of parallel executions
        url: str
            HTTP Request target url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        main_key: str, by default "fullname"
            main-key of dict returns
            This argument's value need to be in module_body list.
        module_body: list[str], by default
            set acquiring values.
            eg: ["fullname", "created_by"]
            by default:
                [
                    "fullname", "category", "name", "title",
                    "created_at", "created_by_unix", "created_by_id",
                    "updated_at", "updated_by_unix", "updated_by_id",
                    "commented_at", "commented_by_unix", "commented_by_id",
                    "parent_fullname", "comments", "size",
                    "rating_votes", "rating", "revisions", "tags", "_tags"
                ]
        <listpages_module_arguments>: **kwargs
            other arguments that can be given to ListPages Module on wikidot.com
            doc: https://www.wikidot.com/doc-modules:listpages-module
            by default:
                "separate": "no", "wrapper": "no", "perPage": "250",
                "offset": "0", "pagetype": "*", "category": "*"
            Usage:
                >>> wikidot.base.page_getdata_mass(......, category="_default", tags="+scp")

    Raises:
        wikidot.exceptions.ArgumentsError(msg, reason)
            reason:
                "main_key_error":
                    main_key argument value is not in module_body argument values list.
        wikidot.exceptions.StatusIsNotOKError(msg, reason)
            reason:
                [status_wikidot_returns]:
                    Wikidot returned status is not "ok".
                    If the site that you request is private, wikidot returns "not_ok"
        wikidot.exceptions.RequestFailedError(msg, html_response_code)
            AMC Request function tried the request several times but it failed.

    Returns:
        None:
            There is no matching page.
        dict:
            {
                <main_key> : {
                    <module_body_value_1>: <value>,
                    <module_body_value_2>: <value>,
                    ....
                }
            }

            If returned value is empty:
                str values:
                    None
                optional int values(created/commented/updated_by_id):
                    None
                not optional int values:
                    0
                datetime values:
                    None

    """
    """
    MEMO:
        1. p＿age_getdataでlistpagesの最初のページを取得、総ページ数とcontentsを返す
        2. 総ページ数-1の回数分、offsetに250*(ページ数-1)を入れてgatherに放り込んで非同期実行
        3. 2の結果群をfor文で回して1のcontentsをupdate
    """

    _args = {
        "url": url,
        "main_key": main_key,
        "module_body": module_body,
        "perPage": 250,
    }

    if kwargs is not None:
        _args.update(kwargs)

    async def _getfirstpage(*, url: str):
        _r = await page_getdata(**_args)
        if _r is None:
            return 0, None
        else:
            return _r["total"], _r["contents"]

    async def _getlastpage(*, limit: int, url: str, total: int):

        sema = asyncio.Semaphore(limit)

        async def __innerfunc(offset):
            async with sema:
                _args.update({
                    "offset": offset,
                    "limit": 250
                })
                _r = await page_getdata(**_args)
                return _r["contents"]

        stmt = []
        for i in range(1, total):
            stmt.append(__innerfunc(offset=250 * i))

        return await asyncio.gather(*stmt)

    total, _r = await _getfirstpage(url=url)

    if _r is not None:
        _rs = await _getlastpage(url=url, limit=limit, total=total)

        for _rr in _rs:
            _r.update(_rr)

    return _r


# --------------------
# PageID
# --------------------


async def page_getid(*, url: str, fullname: str) -> Optional[int]:
    """|Coroutine| Get PageID of specific page

    Arguments:
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        fullname: str
            target page fullname
            eg: "main", "scp-001-jp", "component:theme

    Raises:
        wikidot.exceptions.UnexpectedError(msg, reason)
            reason:
                "undefined":
                    httpx request raises some error.

    Returns:
        int:
            Target page's ID
        None:
            Target page is not found.
    """
    """
    MEMO:
        ・httpxで非同期処理を開き、noredirect,norenderで対象ページにアクセス
            -> ソースコード内の<script>を総当たりし、WIKIREQUEST.info.pageidがあったらint型でreturn
            -> アクセス時に404が返ってきたらNoneをreturn
    """
    async def _innerfunc(*, url, fullname):
        async with httpx.AsyncClient() as client:
            _source = await client.get(
                f"http://{url}/{fullname}/noredirect/true/norender/true",
                headers=variables.request_header,
                timeout=10
            )

            # 404
            if _source.status_code == 404:
                logger.warning(
                    f"GetID | http://{url}/{fullname} - Not Found"
                )
                return None
            elif _source.status_code != 200:
                logger.error(
                    f"GetID | http://{url}/{fullname} - Status code is {_source.status_code}"
                )
                raise

            _contents = bs4(_source.text, 'lxml')
            _contents = _contents.find("head")
            _contents = _contents.find_all(
                "script", attrs={"type": "text/javascript"})
            for _c in _contents:
                _c = _c.string
                if "_public" in str(_c):
                    return None
                elif "WIKIREQUEST.info.pageId" in str(_c):
                    pageid = re.search(
                        r"WIKIREQUEST\.info\.pageId = \d+;", _c).group()
                    pageid = re.search(r"\d+", pageid).group()

                    logger.info(
                        f"GetID | http://{url}/{fullname} - {pageid}"
                    )

                    return int(pageid)

    # Request
    cnt = 1
    end = False
    while end is False:
        try:
            return await _innerfunc(url=url, fullname=fullname)
        except Exception:
            if cnt < 5:
                cnt += 1
                pass
            else:
                raise exceptions.UnexpectedError(
                    "HTTP Request Error occurred while acquiring pageid.", "undefined"
                )


async def page_getid_mass(*, limit: int = 10, url: str, targets: Union[list, tuple]) -> list[tuple[str, Optional[int]]]:
    """|Coroutine| Get PageIDs of multiple pages

    Arguments:
        limit: int, by default 10
            semaphore value = number of parallel executions
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        targets: Union[list, tuple]
            list of target pages' fullname
            eg: ["scp-001", "scp-002", "component:theme"]

     Raises:
        wikidot.exceptions.UnexpectedError(msg, reason)
            reason:
                "undefined":
                    httpx request raises some error.

    Returns:
        list
            [(fullname, pageid), .....]
    """
    """
    MEMO:
        ・page_getidにURLとfullnameを与えてgatherに放り込んで非同期実行
    """

    sema = asyncio.Semaphore(limit)

    async def _innerfunc(**kwargs):
        async with sema:
            pageid = await page_getid(**kwargs)
            return (kwargs["fullname"], pageid)

    stmt = []
    for t in targets:
        stmt.append(_innerfunc(
            **{"url": url, "fullname": t}))

    return await asyncio.gather(*stmt)


# --------------------
# PageSource
# --------------------


async def page_getsource(*, url: str, pageid: int) -> Optional[str]:
    """|AMC| |Coroutine| Get source of specific page

    Arguments:
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        pageid: int
            target page's id

    Raises:
        exceptions.StatusIsNotOKError(msg, status_code)
            [status_wikidot_returns]:
                    Wikidot returned status is not "ok".
                    If status_code is "no_page" or "no_permission", return None
        wikidot.exceptions.UnexpectedError(msg, reason)
            reason:
                "undefined":
                    Error occurred while checking session, and it is not expected.

    Returns:
        None:
            Target page is not found,
                or failed to get source because the source is protected.
        str:
            Target page source
    """
    """
    Memo:
        ・connector.connectでAMCリクエスト
            -> NotFoundErrorやSessionErrorが返ってきたらNoneを返す
            -> 通ったらbs4でページソース部分をget_text()で取得
    """

    try:

        body = {
            "moduleName": "viewsource/ViewSourceModule",
            "page_id": pageid
        }

        _r = await connector.connect(
            body=body,
            url=url,
            unescape=False
        )

        _r_body = _r["body"]

        _r_body_soup = bs4(_r_body, 'lxml')
        _r_body_soup = _r_body_soup.find(
            "div", class_="page-source").get_text()
        return _r_body_soup.strip()
    except exceptions.StatusIsNotOKError as e:
        if e.args[1] == "no_page":
            logger.error(
                f"{pageid} - This page is not found."
            )
            return None
        elif e.args[1] == "no_permission":
            logger.error(
                f"{pageid} - Source of this page is protected. It may be resolved by logging in and creating a session."
            )
            return None
        else:
            raise exceptions.StatusIsNotOKError(
                "Wikidot returns unexpected status", e.args[1])
    except Exception:
        raise exceptions.UnexpectedError(
            "Unexpected Error occurred.", "undefined")


async def page_getsource_mass(*, limit: int = 10, url: str, targets: Union[list, tuple]) -> list[tuple[int, Optional[str]]]:
    """|AMC| |Coroutine| Get source of specific pages

    Arguments:
        limit: int, by default 10
            semaphore value = number of parallel executions
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        targets: Union[list, tuple]
            list of target pages' id

    Raises:
        exceptions.StatusIsNotOKError(msg, status_code)
            [status_wikidot_returns]:
                    Wikidot returned status is not "ok".
                    If status_code is "no_page" or "no_permission", return None
        wikidot.exceptions.UnexpectedError(msg, reason)
            reason:
                "undefined":
                    Error occurred while checking session, and it is not expected.

    Returns:
        list:
            [(pageid, Optional[str]), .....]

    """

    sema = asyncio.Semaphore(limit)

    async def _innerfunc(**kwargs):
        async with sema:
            source = await page_getsource(**kwargs)
            return (kwargs["pageid"], source)

    stmt = []
    for t in targets:
        stmt.append(_innerfunc(
            **{"url": url, "pageid": t}))

    return await asyncio.gather(*stmt)


# --------------------
# Page History
# --------------------


async def page_gethistory(*, url: str, pageid: int):
    async def _get(*, url: str, pageid: int, page: int):
        try:
            _r = await connector.connect(
                url=url,
                body={
                    "moduleName": "history/PageRevisionListModule",
                    "perpage": "10000",
                    "page": page,
                    "options": "{'all':true}",
                    "page_id": pageid
                }
            )
        except exceptions.StatusIsNotOKError as e:
            logger.error(f"Status is not OK, {e.args[1]}, {pageid}")
            return 1, []

        _r_body = bs4(_r["body"], "lxml")

        # pager
        pager = _r_body.find("div", class_="pager")
        if pager is not None:
            total = int(pager.find_all("span", class_="target")[-2].string)
        else:
            total = 1

        # parse
        table = _r_body.find("table", class_="page-history")

        r = []

        for tr in table.find_all("tr"):
            if "id" in tr.attrs and "revision-row-" in str(tr["id"]):
                rev_id = int(str(tr["id"]).replace("revision-row-", ""))
                td = tr.find_all("td")
                rev_no = int(str(td[0].get_text()).strip().removesuffix("."))
                flags = []
                _flags = td[2].find_all("span")
                for _flag in _flags:
                    _flag = _flag.get_text()
                    if _flag == "N":
                        _flag = "new"
                    elif _flag == "S":
                        _flag = "source"
                    elif _flag == "T":
                        _flag = "title"
                    elif _flag == "R":
                        _flag = "rename"
                    elif _flag == "A":
                        _flag = "tag"
                    elif _flag == "M":
                        _flag = "meta"
                    elif _flag == "F":
                        _flag = "file"
                    else:
                        _flag = "undefined"
                    flags.append(_flag)
                author_name, author_unix, author_id = author_parser(td[4].find("span", class_="printuser", recursive=False))
                time = odate_parser(td[5].find("span", class_="odate"))
                comment = td[6].get_text()
                if comment == "":
                    comment = None

                r.append({
                    "rev_id": rev_id,
                    "rev_no": rev_no,
                    "author": {
                        "name": author_name,
                        "unix": author_unix,
                        "id": author_id
                    },
                    "time": time,
                    "flags": flags,
                    "comment": comment
                })

        return total, r

    total, r = await _get(url=url, pageid=pageid, page=1)

    if total != 1:
        page = 2
        while page <= total:
            total, _r = await _get(url=url, pageid=pageid, page=page)
            r.extend(_r)
            page += 1

    return r


async def page_gethistory_mass(*, limit: int = 10, url: str, targets: list[int]):
    sema = asyncio.Semaphore(limit)

    async def _innerfunc(**kwargs):
        async with sema:
            history = await page_gethistory(**kwargs)
            return (kwargs["pageid"], history)

    stmt = []
    for t in targets:
        stmt.append(_innerfunc(**{"url": url, "pageid": t}))

    _r = await asyncio.gather(*stmt)
    r = []
    for _r_id, _r_list in _r:
        r.append((_r_id, tuple(_r_list)))
    return r


# --------------------
# PageEdit
# --------------------


@decorator.require_session
async def page_edit(*, url: str, fullname: str, pageid: Optional[int] = None, title: str = "", content: str = "", comment: str = "", forceedit: bool = False) -> bool:
    """|AMC| |Coroutine| |SessionRequired| Edit specific page

    Arguments:
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        fullname: str
            target page fullname
        pageid: Optional[int], by default None
            target page's id
            if None, get automatically.
            if you want to create new page, plase set this argument None.
        title: str, by default ""
            page title
        content: str, by default ""
            page content
        comment: str, by default ""
            edit desctiption
        forceedit: bool, by default False
            Whether to automatically unlock when the page is locked

    Raises:
        wikidot.exceptions.StatusIsNotOKError(msg, status_code)
            The status returned by Wikidot was not OK
        wikidot.exceptions.RequestFailedError(msg, html_response_code)
            Function tried the request several times but it failed.

    Returns:
        bool
            return True when action successful.

    """
    _f_newpage = False

    # fullnameしか与えられなかったら自動でpageidを取りに行く
    if fullname is not None and pageid is None:
        pageid = await page_getid(url=url, fullname=fullname)
        # 該当ページがなかったら新規作成フラグを立てる
        if pageid is None:
            _f_newpage = True
            logger.info(
                f"New Page: http://{url}/{fullname}"
            )

    # Lockを強制解除するか否か
    if forceedit is True:
        _body = {
            "mode": "page",
            "moduleName": "edit/PageEditModule",
            "page_id": pageid,
            "force_lock": "yes"
        }
    else:
        _body = {
            "mode": "page",
            "moduleName": "edit/PageEditModule",
            "page_id": pageid
        }

    # Editorを起動 lockidとrevidを取る
    if _f_newpage is False:
        logger.info(
            f"OpenEditor | url: {url}, page: {fullname}({pageid})"
        )
        _editor = await connector.connect(
            url=url,
            body=_body
        )
        if "locked" in _editor or "other_locks" in _editor:
            raise exceptions.StatusIsNotOKError("Target page is locked.", "page_locked")

    else:
        pageid = ""
        _editor = {
            "lock_id": "",
            "lock_secret": "",
            "page_revision_id": ""
        }

    # Save
    logger.info(
        f"Edit | page: {fullname}({pageid}), title: {title}"
    )
    await connector.connect(
        url=url,
        body={
            "action": "WikiPageAction",
            "event": "savePage",
            "moduleName": "Empty",
            "mode": "page",
            "lock_id": _editor["lock_id"],
            "lock_secret": _editor["lock_secret"],
            "page_revision_id": _editor["page_revision_id"],
            "wiki_page": fullname,
            "page_id": pageid,
            "title": title,
            "source": content,
            "comments": comment
        }
    )


# --------------------
# ParentPage
# --------------------


@decorator.require_session
async def page_setparent(*, url: str, pageid: int, parentpage: str) -> bool:
    """|AMC| |Coroutine| |SessionRequired| set parent page

    Arguments:
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        pageid: int
            target page's id
        parentpage: str
            fullname of page want to set as parent

    Raises:
        wikidot.exceptions.StatusIsNotOKError(msg, status_code)
            The status returned by Wikidot was not OK
        wikidot.exceptions.RequestFailedError(msg, html_response_code)
            Function tried the request several times but it failed.

    Return:
        bool:
            return true if request is successful.
    """
    logger.info(
        f"SetParent | url: {url}, target: {pageid}, parent: {parentpage}"
    )
    body = {
        "action": "WikiPageAction",
        "event": "setParentPage",
        "moduleName": "Empty",
        "pageId": str(pageid),
        "parentName": parentpage
    }
    await connector.connect(
        body=body,
        url=url
    )

    return True


@decorator.require_session
async def page_setparent_mass(*, limit: int = 10, url: str, targets: Union[list, tuple]) -> list[bool]:
    """|AMC| |Coroutine| |SessionRequired| set parent page

    Arguments:
        limit: int, by default 10
            semaphore value = number of parallel executions
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        targets: Union[list, tuple]
            list of target page's id and parentpage's fullname
            [(target_id, parent_fullname), ......]

    Raises:
        None

    Returns:
        bool:
            Whether the parent page setting was successful
            when failed, returns False
    """
    sema = asyncio.Semaphore(limit)

    async def _innerfunc(**kwargs):
        async with sema:
            try:
                _r = await page_setparent(**kwargs)
                return _r
            except Exception:
                logger.error(
                    f"{kwargs['pageid']} - failed to set the parent page.",
                    exc_info=True
                )
                return False

    stmt = []
    for t, parentpage in targets:
        stmt.append(_innerfunc(url=url, parentpage=parentpage, pageid=t))

    await asyncio.gather(*stmt)


# --------------------
# RenamePage
# --------------------


@decorator.require_session
async def page_rename(*, url: str, pageid: int, fullname: str):
    try:
        await connector.connect(
            url=url,
            body={
                "action": "WikiPageAction",
                "event": "renamePage",
                "moduleName": "Empty",
                "page_id": pageid,
                "new_name": fullname
            }
        )
        return True
    except exceptions.StatusIsNotOKError as e:
        if e.args[1] == "page_exists":
            logger.error(
                f"Rename | The renamed page already exists. | {pageid}, {fullname}"
            )
        raise


@decorator.require_session
async def page_rename_mass(*, limit: int = 10, url: str, targets: list):
    sema = asyncio.Semaphore(limit)

    async def _innerfunc(**kwargs):
        async with sema:
            try:
                status = await page_rename(**kwargs)
            except Exception:
                status = False
            return (kwargs["pageid"], kwargs["fullname"], status)

    stmt = []
    for t in targets:
        stmt.append(
            _innerfunc(**{
                "url": url,
                "pageid": t[0],
                "fullname": t[1]
            })
        )

    await asyncio.gather(*stmt)


# --------------------
# Tags
# --------------------


@decorator.require_session
async def tag_set(*, url: str, pageid: int, tags: Union[list, tuple]) -> bool:
    """|AMC| |Coroutine| Set tags to specific page.

    Arguments:
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        pageid: int
            target page id
        tags: Union[list, tuple]
            list of tags want to set

    Raises:
        wikidot.exceptions.StatusIsNotOKError(msg, status_code)
            The status returned by Wikidot was not OK
        wikidot.exceptions.RequestFailedError(msg, html_response_code)
            Function tried the request several times but it failed.

    Returns:
        bool:
            return True when action successful.

    """
    logger.info(
        f"TagSet | target: {pageid}, tags: {' '.join(tags)}"
    )
    body = {
        "action": "WikiPageAction",
        "event": "saveTags",
        "moduleName": "Empty",
        "tags": " ".join(tags),
        "pageId": pageid
    }
    r = await connector.connect(
        body=body,
        url=url
    )

    return r


@decorator.require_session
async def tag_replace(*, limit: int = 10, url: str, before: str, after: str, selector: Optional[dict] = None) -> list[bool]:
    """|AMC| |Coroutine| Replaces the tag on the page that matches the selector

    Arguments:
        limit: int, by default 10
            semaphore value = number of parallel executions
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        before: str
            tag you want to replace
        after: str
            tag after replacement
        selector: Optional[dict]
            custom getdata's arguments.
            if None, use {"tags": +[before]} automatically.

    Returns:
        list[bool]:
            list of action result

    """

    if selector is None or "tags" not in selector:
        selector["tags"] = "+" + before

    _r = await page_getdata_mass(limit=limit, url=url, module_body=["fullname", "tags", "_tags"], **selector)

    targets = {t["fullname"]: [t["tags"] + t["_tags"], None]
               for t in _r.values()}

    ids = await page_getid_mass(limit=limit, url=url, targets=[t for t in targets])

    for fullname, pageid in ids:
        targets[fullname][1] = pageid

    sema = asyncio.Semaphore(limit)

    async def _innerfunc(tags, pageid):
        async with sema:
            if before in tags:
                tags.remove(before)
            tags.append(after)
            try:
                return await tag_set(url=url, pageid=pageid, tags=tags)
            except Exception:
                logger.error(
                    "TagSet | failed to set tags."
                )
                logger.debug(
                    " ",
                    exc_info=True
                )
                return False

    stmt = []
    for tags, pageid in targets.values():
        stmt.append(_innerfunc(tags, pageid))

    return await asyncio.gather(*stmt)


@decorator.require_session
async def tag_reset(*, limit: int = 10, url: str, tagset: Union[list, tuple], selector: dict) -> list[bool]:
    """|AMC| |Coroutine| Replaces the tag on the page that matches the selector

    Arguments:
        limit: int, by default 10
            semaphore value = number of parallel executions
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        tagset: list
            tags you want to set
        selector: dict
            custom getdata's arguments.

    Returns:
        list[bool]:
            list of action result

    """

    _r = await page_getdata_mass(limit=limit, url=url, module_body=["fullname"], **selector)

    targets_fullname = [t for t in _r]

    ids = await page_getid_mass(limit=limit, url=url, targets=targets_fullname)

    targets_ids = [t[1] for t in ids]

    sema = asyncio.Semaphore(limit)

    async def _innerfunc(pageid):
        async with sema:
            try:
                return await tag_set(url=url, pageid=pageid, tags=tagset)
            except Exception:
                logger.error(
                    "Failed to set tag.",
                    exc_info=True
                )
                return False

    stmt = []
    for pageid in targets_ids:
        stmt.append(_innerfunc(pageid))

    return await asyncio.gather(*stmt)


# --------------------
# Forum
# --------------------


async def forum_getcategories(*, url: str, includehidden: bool = True) -> list[tuple[int, str]]:
    """|Coroutine| Get forum categories.

    Arguments:
        url: str
            target site url
            eg: "scp-jp.wikidot.com", "scpwiki.com"
        includehidden: True, by dafault True
            Whether to get hidden categories

    Returns:
        list[tuple[int, str]]
            [(category_id, category_name), ...]

    """

    _r = await connector.connect(
        url=url,
        body={
            "moduleName": "forum/ForumStartModule",
            "hidden": includehidden
        }
    )

    result = []

    _r = bs4(_r["body"], 'lxml')
    _cats = _r.find_all("td", class_="name")

    for _cat in _cats:
        title = _cat.find("div", class_="title").find("a")
        catid = title["href"]
        catid = re.search(r'\d+', catid).group()
        catid = int(catid)
        catname = title.string
        result.append((catid, catname))

    return result


async def forum_getthreads_percategory(*, limit: int = 10, url: str, categoryid: int) -> dict:
    """|Coroutine| get all threads data in specific category

    Arguments:
        limit: int, by default 10
            semaphore value = number of parallel executions
        url: str
            target site url
        categoryid: int
            target forum category id

    Returns:
        dict
            {
                threadid: {
                    "title": thread-title(str),
                    "author_id": author-account-id(int),
                    "author_unix": author-account-unixname(str),
                    "posts": number-of-posts(int),
                    "start": datetime-thread-started(datetime)
                }
            }

    """

    async def _getthreadsspecificpage(*, url: str, categoryid: int, page: int):
        # AMC Request
        _r = await connector.connect(
            url=url,
            body={
                "wikidot_token7": "123456",
                "moduleName": "forum/ForumViewCategoryModule",
                "c": categoryid,
                "p": page
            }
        )
        # HTML Parse
        _r = bs4(_r["body"], 'lxml')
        # get numbers of threads and pages from statistics
        statistics = _r.find(
            "div", class_="statistics").get_text("::").split("::")
        num_threads = int(re.search(r'\d+', statistics[0]).group())
        num_pages = math.ceil(num_threads / 20)
        threads = _r.find_all("tr", class_="")
        result = {}
        for thread in threads:
            titleelem = thread.find("div", class_="title").find("a")
            threadid = titleelem["href"]
            threadid = int(re.search(r'\d+', threadid).group())
            threadtitle = titleelem.string
            startedelem = thread.find("td", class_="started")
            startdate = odate_parser(startedelem.find("span", class_="odate"))
            author = startedelem.find("span", class_="printuser")
            author_name, author_unix, author_id = author_parser(author)
            posts = int(thread.find("td", class_="posts").string)
            result.update({
                threadid: {
                    "title": str(threadtitle),
                    "author": {
                        "author_id": int(author_id) if author_id is not None else author_id,
                        "author_unix": str(author_unix),
                        "author_name": str(author_name)
                    },
                    "posts": int(posts),
                    "start": startdate
                }
            })

        return num_pages, result

    async def _getlastpage(*, limit: int, url: str, categoryid: int, totalpages: int):

        sema = asyncio.Semaphore(limit)

        async def __innerfunc(url: str, page: int):
            async with sema:
                _r = await _getthreadsspecificpage(url=url, page=page, categoryid=categoryid)
                return _r[1]

        stmt = []
        for i in range(2, totalpages + 1):
            stmt.append(__innerfunc(url=url, page=i))

        return await asyncio.gather(*stmt)

    totalpages, _r = await _getthreadsspecificpage(url=url, categoryid=categoryid, page=1)

    if totalpages > 1:
        _rs = await _getlastpage(limit=limit, url=url, categoryid=categoryid, totalpages=totalpages)

        for _rr in _rs:
            _r.update(_rr)

    return _r


async def forum_getthreads_mass(*, limit: int = 10, url: str, includehidden: bool = True) -> list[dict]:

    _cats = await forum_getcategories(url=url, includehidden=includehidden)

    _r = []

    for _cat in _cats:
        _catid, _cattitle = _cat

        _ths = await forum_getthreads_percategory(limit=limit, url=url, categoryid=_catid)

        _r.append({
            "category_id": _catid,
            "category_title": _cattitle,
            "category_threads": _ths
        })

    return _r


async def forum_getposts(*, url: str, threadid: int, page: int):

    def _parser(post_element):
        parent = post_element.parent.parent
        if parent.name != "body":
            parentid = int(parent.find("div", class_="post", recursive=False)["id"].replace("post-", ""))
        else:
            parentid = None
        postid = int(str(post_element["id"]).replace("post-", ""))
        _wrapper = post_element.find("div", class_="long", recursive=False)
        _head = _wrapper.find("div", class_="head")
        title = _head.find("div", class_="title").get_text()
        title = title.strip()
        _info = _head.find("div", class_="info")
        _authorelem = _info.find("span", class_="printuser")
        author_name, author_unix, author_id = author_parser(_authorelem)
        postdate = odate_parser(_info.find("span", class_="odate"))
        content = _wrapper.find("div", class_="content").get_text()

        return {
            "id": postid,
            "title": title,
            "author": {
                "name": author_name,
                "unixname": author_unix,
                "id": author_id
            },
            "pubdate": postdate,
            "content": content,
            "parentid": parentid
        }

    _r = await connector.connect(
        url=url,
        body={
            "moduleName": "forum/ForumViewThreadPostsModule",
            "pageNo": str(page),
            "t": str(threadid)
        }
    )

    # parse
    _r_body = bs4(_r["body"], 'lxml')

    # pager
    pager = _r_body.find("div", class_="pager")
    if pager is not None:
        total = int(pager.find_all("span", class_="target")[-2].string)
    else:
        total = 1

    posts = _r_body.find_all("div", class_="post", recursive=True)

    r = []

    if posts is None:
        return None
    else:
        for post in posts:
            _r = _parser(post)
            r.append(_r)

    return total, r


async def forum_getposts_perthread(*, limit: int = 10, url: str, threadid: int):

    total, r = await forum_getposts(url=url, threadid=threadid, page=1)

    async def _getallpage():
        sema = asyncio.Semaphore(limit)

        async def __innerfunc(page):
            async with sema:
                _r = await forum_getposts(url=url, threadid=threadid, page=page)
                return _r[1]

        stmt = []
        for i in range(2, total + 1):
            stmt.append(__innerfunc(page=i))

        return await asyncio.gather(*stmt)

    _r = await _getallpage()

    for _rr in _r:
        r.extend(_rr)

    return r


async def forum_getparentpagefullname(*, url: str, threadid: int, forumcategoryname: str = "forum"):
    async with httpx.AsyncClient() as client:
        logger.debug(
            f"Get parentpage: http://{url}/{forumcategoryname}/t-{threadid}"
        )
        _source = await client.get(
            f"http://{url}/{forumcategoryname}/t-{threadid}",
            timeout=10
        )

        # 404
        if _source.status_code != 200:
            raise exceptions.RequestFailedError(
                "Unexpected status code returns",
                _source.status_code
            )

        contents = bs4(_source.text, 'lxml')
        fullname = contents.find("div", id="page-title").find("a")["href"]
        fullname = fullname.lstrip("/")
        return fullname


async def forum_getparentpage(*, url: str, threadid: int, forumcategoryname: str = "forum"):
    fullname = await forum_getparentpagefullname(url=url, threadid=threadid, forumcategoryname=forumcategoryname)
    pageid = await page_getid(url=url, fullname=fullname)
    return (fullname, pageid)


async def forum_getpagediscussion(*, url: str, pageid: int):
    _r = await connector.connect(
        url=url,
        body={
            "moduleName": "forum/ForumCommentsListModule",
            "pageId": pageid
        }
    )

    threadid = re.search(r"WIKIDOT\.forumThreadId = \d+;", _r["body"]).group()
    threadid = re.search(r"\d+", threadid).group()

    return int(threadid)


@decorator.require_session
async def forum_post(*, url: str, threadid: int, parentid: Optional[int] = None, title: str = "", content: str):
    await connector.connect(
        url=url,
        body={
            "threadId": str(threadid),
            "parentId": str(parentid) if parentid is not None else "",
            "title": title,
            "source": content,
            "action": "ForumAction",
            "event": "savePost",
            "moduleName": "Empty"
        }
    )


@decorator.require_session
async def forum_edit(*, url: str, threadid: int, postid: int, title: str = "", content: str):
    _pr = connector.connect(
        url=url,
        body={
            "moduleName": "forum/sub/ForumEditPostFormModule",
            "threadId": threadid,
            "postId": postid
        }
    )

    currentrevisionid = bs4(_pr["body"], 'lxml')
    currentrevisionid = int(currentrevisionid.find("input", name="currentRevisionId")["value"])

    connector.connect(
        url=url,
        body={
            "action": "ForumAction",
            "event": "saveEditPost",
            "moduleName": "Empty",
            "postId": postid,
            "currentRevisionId": currentrevisionid,
            "title": title,
            "source": content
        }
    )


# --------------------
# Forum - RSS
# --------------------


async def rss_get(*, url: str, code: str):
    r = []

    # mode
    if code == "posts":
        mode = "p"
    elif code == "threads":
        mode = "t"
    elif "ct" in code:
        mode = "t"
    else:
        mode = "p"

    feed = feedparser.parse(f"http://{url}/feed/forum/{code}.xml")
    entries = feed.entries

    for entry in reversed(entries):
        if mode == "t":
            link = entry.id
            thread_id = int(link.split("/t-")[1])
            title = entry.title
            summary = entry.summary
            pubdate = datetime.fromtimestamp(mktime(entry.published_parsed))
            username = entry.wikidot_authorname
            userid = entry.wikidot_authoruserid
            content = bs4(entry.content[0]["value"], 'lxml').get_text()
            r.append({
                "link": link,
                "thread_id": thread_id,
                "title": title,
                "summary": summary,
                "pubdate": pubdate,
                "author_name": username,
                "author_id": userid,
                "content": content
            })
        elif mode == "p":
            link = entry.id
            ids = link.split("/t-")[1].split("#post-")
            entryid = int(ids[0])
            threadid = int(ids[1])
            title = entry.title
            pubdate = datetime.fromtimestamp(mktime(entry.published_parsed))
            username = entry.wikidot_authorname
            userid = entry.wikidot_authoruserid
            content = bs4(entry.content[0]["value"], 'lxml').get_text()

            r.append({
                "link": link,
                "post_id": entryid,
                "thread_id": threadid,
                "title": title,
                "pubdate": pubdate,
                "author_name": username,
                "author_id": userid,
                "content": content
            })

    return r


# --------------------
# User
# --------------------


async def site_getmembers(*, url: str, page: int):

    _r = await connector.connect(
        url=url,
        body={
            "moduleName": "membership/MembersListModule",
            "page": page,
            "group": "",
            "order": "",
        }
    )

    # parse
    _r_body = bs4(_r["body"], 'lxml')

    # pager
    pager = _r_body.find("div", class_="pager")
    if pager is not None:
        total = int(pager.find_all("span", class_="target")[-2].string)
    else:
        total = 1

    members = _r_body.find_all("tr")

    r = []

    if members is None:
        return None
    else:
        for member in members:
            user_name, user_unix, user_id = author_parser(member.find("span", class_="printuser"))
            joindate = odate_parser(member.find("span", class_="odate"))
            r.append((user_name, user_unix, user_id, joindate))

    return total, r


async def site_getmembers_mass(*, limit: int = 10, url: str):
    total, r = await site_getmembers(url=url, page=1)

    async def _getallpage():
        sema = asyncio.Semaphore(limit)

        async def __innerfunc(page):
            async with sema:
                _r = await site_getmembers(url=url, page=page)
                return _r[1]

        stmt = []
        for i in range(2, total + 1):
            stmt.append(__innerfunc(page=i))

        return await asyncio.gather(*stmt)

    _r = await _getallpage()

    for _rr in _r:
        r.extend(_rr)

    return r


# --------------------
# Vote
# --------------------


async def vote_getvoter(*, url: str, pageid: int):
    try:
        _r = await connector.connect(
            url=url,
            body={
                "moduleName": "pagerate/WhoRatedPageModule",
                "pageId": pageid
            }
        )
    except exceptions.StatusIsNotOKError as e:
        logger.error(f"Status is not OK, {e.args[1]}, {pageid}")
        return []

    _r = bs4(_r["body"], "lxml")

    voters = _r.find_all("span", class_="printuser", recursive=True)

    r = []

    for voter in voters:
        user_name, user_unix, user_id = author_parser(voter)
        res = voter.next_sibling.next_sibling.get_text().strip()
        if res == "+":
            res = 1
        elif res == "-":
            res = -1
        else:
            res = int(res)
        r.append((user_name, user_unix, user_id, res))

    return r


async def vote_getvoter_mass(*, limit: int = 10, url: str, targets: list[int]):
    sema = asyncio.Semaphore(limit)

    async def _innerfunc(**kwargs):
        async with sema:
            voters = await vote_getvoter(**kwargs)
            return (kwargs["pageid"], voters)

    stmt = []
    for t in targets:
        stmt.append(_innerfunc(**{"url": url, "pageid": t}))

    return await asyncio.gather(*stmt)


@decorator.require_session
async def vote_postvote(*, url: str, pageid: int, vote: int):
    if vote not in (1, -1):
        raise exceptions.ArgumentsError("'vote' argument accepts only 1 and -1.", "vote_point_error")
    try:
        _r = await connector.connect(
            url=url,
            body={
                "action": "RateAction",
                "event": "ratePage",
                "moduleName": "Empty",
                "pageId": pageid,
                "points": vote,
                "force": "yes"
            }
        )

        return int(_r["points"])
    except exceptions.StatusIsNotOKError as e:
        if e.args[1] == "not_ok":
            logger.error("PostVote | Target page may not be able to vote.")
            return None
        else:
            raise


@decorator.require_session
async def vote_cancelvote(*, url: str, pageid: int):
    try:
        _r = await connector.connect(
            url=url,
            body={
                "action": "RateAction",
                "event": "cancelVote",
                "moduleName": "Empty",
                "pageId": pageid
            }
        )
        return int(_r["points"])
    except exceptions.StatusIsNotOKError as e:
        if e.args[1] == "not_ok":
            logger.error("PostVote | Target page may not be able to vote.")
            return None
        else:
            raise


# --------------------
# File
# --------------------


async def file_getlist(*, url: str, pageid: int):

    _r = await connector.connect(
        url=url,
        body={
            "moduleName": "files/PageFilesModule",
            "page_id": pageid
        }
    )

    _r = bs4(_r["body"], "lxml")

    _files = _r.find("table", class_="page-files")

    if _files is not None:
        r = []
        _files = _files.find("tbody").find_all("tr")
        for _file in _files:
            if "id" in _file.attrs and "file-row" in str(_file["id"]):
                fileid = int(str(_file["id"]).replace("file-row-", ""))
                _td = _file.find_all("td")
                _filelink = _td[0].find("a")
                filename = _filelink.get_text()
                link = f"http://{url}{_filelink['href']}"
                mime = _td[1].find("span")["title"]
                size = _td[2].get_text().strip()
                if "Bytes" in size:
                    size = float(size.replace("Bytes", "").strip())
                elif "kB" in size:
                    size = float(size.replace("kB", "").strip()) * 1000
                elif "MB" in size:
                    size = float(size.replace("MB", "").strip()) * 1000000

                size = int(size)

                r.append((fileid, filename, link, mime, size))

    else:
        r = None

    return pageid, r


async def file_getlist_mass(*, limit: int = 10, url: str, targets: list[int]):
    sema = asyncio.Semaphore(limit)

    async def _innerfunc(**kwargs):
        async with sema:
            history = await file_getlist(**kwargs)
            return (kwargs["pageid"], history)

    stmt = []
    for t in targets:
        stmt.append(_innerfunc(**{"url": url, "pageid": t}))

    r = []

    _r = await asyncio.gather(*stmt)

    for _r_id, _r_list in _r:
        r.append((_r_id, _r_list))

    return r


# TODO: Fileinfoからデータ抜く関数

# MEMO: fileuploadわからん なにこれ？


# --------------------
# SiteHistory
# --------------------


async def site_gethistory(*, url: str, limitpage: Optional[int] = None):
    async def _get(*, url: str, page: int):
        _r = await connector.connect(
            url=url,
            body={
                "moduleName": "changes/SiteChangesListModule",
                "perpage": "1000",
                "page": page,
                "options": "{'all':true}"
            }
        )

        _r_body = bs4(_r["body"], "lxml")

        r = []

        for item in _r_body.find_all("div", class_="changes-list-item"):
            # comments
            if item.find("div", class_="comments") is not None:
                comments = item.find("div", class_="comments").get_text().strip()
            else:
                comments = None

            # table
            titleelem = item.find("td", class_="title").find("a")
            title = titleelem.get_text().strip()
            if "\t" in title:
                title = str(title.split("\t")[-1])
            fullname = str(titleelem["href"]).replace("/", "").strip()
            date = odate_parser(item.find("td", class_="mod-date").find("span", class_="odate"))
            rev_no = item.find("td", class_="revision-no").get_text().strip()
            rev_no = re.search(r"\d+", rev_no)
            if rev_no is None:
                rev_no = 0
            else:
                rev_no = int(rev_no.group())
            if "deleted" not in item.find("span", class_="printuser")["class"]:
                authorelem = item.find("span", class_="printuser").find("a")
                author_name = authorelem.get_text()
                author_unix = str(authorelem["href"]).replace("http://www.wikidot.com/user:info/", "").strip()
                author_id = int(str(authorelem["onclick"]).replace("WIKIDOT.page.listeners.userInfo(", "").replace("); return false;", "").strip())
            else:
                author_name, author_unix, author_id = author_parser(item.find("span", class_="printuser"))

            flags = []
            _flags = item.find("td", class_="flags").find_all("span")
            for _flag in _flags:
                _flag = _flag.get_text()
                if _flag == "N":
                    _flag = "new"
                elif _flag == "S":
                    _flag = "source"
                elif _flag == "T":
                    _flag = "title"
                elif _flag == "R":
                    _flag = "rename"
                elif _flag == "A":
                    _flag = "tag"
                elif _flag == "M":
                    _flag = "meta"
                elif _flag == "F":
                    _flag = "file"
                else:
                    _flag = "undefined"
                flags.append(_flag)

            r.append((title, fullname, date, rev_no, author_name, author_unix, author_id, flags, comments))

        return r

    if limitpage is None:
        pages = await page_getdata_mass(url=url, module_body=["fullname", "revisions"])
        cnt = 0
        for page in pages.values():
            cnt += page["revisions"]
        limitpage = math.ceil(cnt / 1000)

    sema = asyncio.Semaphore(10)

    async def _innerfunc(page):
        async with sema:
            return await _get(url=url, page=page)

    stmt = []
    for i in range(1, limitpage + 1):
        stmt.append(
            _innerfunc(i)
        )

    _rr = await asyncio.gather(*stmt)

    r = []
    for _r in _rr:
        r.extend(_r)

    return r
