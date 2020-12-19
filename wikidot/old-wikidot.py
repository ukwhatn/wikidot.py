"""
wikidot.py - Package for connect and execute commands on wikidot.com

author: ukwhatn

version: 1.0.0

Requirements
------------
bs4
datetime
feedparser
html
math
re
requests
"""

# Request
import requests
# times
from datetime import datetime
# Parse HTML
from bs4 import BeautifulSoup as bs4
# Parse xml
import feedparser
# Decode HTML SpecialChars
import html
# Regular expression operation
import re

# Expression
import math


# Custom Exceptions

class LoginError(Exception):
    pass


class AjaxError(Exception):
    pass


class ModuleError(Exception):
    pass


class Wikidot():
    def __init__(self):
        """Set default values."""
        self.acc_user = "anonymous"
        self.acc_sessid = "anonymous"
        self.req_header = {
            "Cookie": "wikidot_token7=123456;",
            "Content-Type": ("application/x-www-form-urlencoded;"
                             "charset=UTF-8")
        }

    def login(self, user="", password=""):
        """Login to wikidot."""
        if user != "" and password != "":
            try:
                # ログイン操作を行ってSessionIDを取得
                _login = requests.post("https://www.wikidot.com/default--flow/login__LoginPopupScreen", {
                    'login': user,
                    'password': password,
                    'action': 'Login2Action',
                    'event': 'login'
                })
                self.acc_sessid = _login.cookies['WIKIDOT_SESSION_ID']
                self.acc_user = user
                # __init__で設定したheader配列を上書き
                self.req_header = {
                    "Cookie": (f"wikidot_token7=123456;"
                               f"WIKIDOT_SESSION_ID={self.acc_sessid};"),
                    "Content-Type": ("application/x-www-form-urlencoded;"
                                     "charset=UTF-8")
                }
                return user
            except Exception as e:
                # ログイン中にエラー発生
                raise LoginError("Error occured while logging in to wikidot.")
        # ログイン情報なし
        else:
            raise LoginError("Can't get parameters required to login.")

    def logout(self):
        # ログイン済み
        if self.acc_user != "anonymous":
            # ログアウト操作を行う
            logout = requests.post(
                "http://www.wikidot.com/ajax-module-connector.php/",
                headers=self.req_header,
                data={
                    "wikidot_token7": "123456",
                    "action": "Login2Action",
                    "event": "logout",
                    "moduleName": "Empty"
                })
            # 戻り値
            logout = logout.json()
            if logout["status"] == "ok":
                return True
            else:
                return False

    def __del__(self):
        # インスタンス削除時にログアウトを行う
        self.logout()

    def getpageid(self, url, fullname):
        # HTMLスクレイピングでPageIDを取得
        try:
            res = requests.get(
                f"http://{url}/{fullname}/noredirect/true")
            contents = bs4(res.text, 'lxml')
            contents = contents.find("head")
            contents = contents.find_all(
                "script", attrs={"type": "text/javascript"})
            for content in contents:
                content = content.string
                if "WIKIREQUEST.info.pageId" in str(content):
                    pageid = re.search(
                        r"WIKIREQUEST\.info\.pageId = \d+;", content).group()
                    pageid = re.search(r"\d+", pageid).group()

                    return int(pageid)

        except Exception as e:
            raise ModuleError("Can't acquire pageid.")

        return result

    def ajaxcon(self, **kwargs):
        """
        Get specific data from ajax-module-connector.php.

        Parameters
        ----------
            **kwargs:
                body : dict (default : {})
                    HTTP Request body sent to ajaxcon.
                url : str (default : "scp-jp.wikidot.com")
                    HTTP Request target url

        Returns
        -------
            return dict:
                Obtained JSON -> convert to dict -> unescape contents
        """
        # default arguments
        for kw in ("body", "url"):
            if kw not in kwargs:
                if kw in ("body"):
                    kwargs[kw] = {}
                elif kw in ("url"):
                    kwargs[kw] = "scp-jp.wikidot.com"

        # HTTP Request Body
        body = {
            "wikidot_token7": "123456"
        }
        body.update(kwargs["body"])

        # Request
        res = requests.post(
            f"http://{kwargs['url']}/ajax-module-connector.php/",
            data=body, headers=self.req_header)

        try:
            res_json = res.json()
        except Exception as e:
            raise AjaxError("Acquired data is not json format.")

        # wrong_token7
        if res_json['status'] != "ok":
            raise AjaxError(f"Wikidot returns error, such as wrong_token7 - {res_json['status']}")

        if "body" in res_json:
            res_json["body"] = html.unescape(res_json["body"])

        return res_json

    def listpages(self, **kwargs):
        """
        Post to ajaxcon() with listpages parameters and \
                        get specific data from ajax-module-connector.php.

        Parameters
        ----------
            **kwargs:
                <module_args>:
                    set custom parameters to post to ajaxcon.

                nowtime:
                    set acquired datetime to align database

                main_key: (default: fullname)
                    key of return dict

        Returns
        -------
            return dict:
                status:
                    "success" (str)

                pages:
                    current: int
                        current page number
                    total: int
                        number of total pages from pager

                contents: dict
                    obtained and parsed dict
        """
        # Default Request Body
        if "module_body" in kwargs:
            module_body = kwargs["module_body"]
        else:
            module_body = [
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

        requestbody = {
            "moduleName": "list/ListPagesModule",
            "separate": "no",
            "wrapper": "no",
            "perPage": "250",
            "offset": "0",
            "pagetype": "*",
            "category": "*",
            "module_body": "<page>" + "".join(
                map(
                    "<set><n> {0} </n><v> %%{0}%% </v></set>".format,
                    module_body)) + "</page>"
        }

        if "main_key" not in kwargs:
            kwargs["main_key"] = "fullname"

        c_body = kwargs.copy()

        for key in ("nowtime", "module_body", "main_key", "url"):
            if key in c_body:
                del c_body[key]

        requestbody.update(c_body)

        # Request
        try:
            listpages = self.ajaxcon(url=kwargs["url"], body=requestbody)
        except AjaxError as e:
            raise ModuleError("Error occured while connecting ajaxcon.")

        # Dict to Return Result
        contents = {}

        # parse
        content = bs4(listpages["body"], 'lxml')

        # pager exists (= there are multiple pages) or not
        pager = content.find("div", class_="pager")
        if pager is not None:
            currentpage = int(pager.find("span", class_="current").string)
            totalpage = int(pager.find_all("span", class_="target")[-2].string)
        else:
            currentpage = 1
            totalpage = 1

        # acquire per-page data
        pages = content.find_all("page")

        # Can't found page contents
        if not pages:
            return {"status": "error", "error_code": "not_found_effective_data"}

        # Contain to dict page by page
        # if empty:
            # datetime: 1000-01-01 00:00 -> "_at" values
            # int: 0 -> int values
            # list: [] -> tags
            # str: "" -> others
        for page in content.find_all("page"):
            # result array
            tmp_dic = {}
            # options in a page
            opts = page.find_all("set")

            if "nowtime" in kwargs:
                tmp_dic["acquire"] = kwargs["nowtime"]

            for opt in opts:
                # default values
                # separate name and value
                name = opt.find("n").string.strip()
                value = opt.find("v")
                # for odate values
                if value.find("span") is None:
                    value = value.string
                else:
                    value = value.find("span").string

                if value is not None:
                    value = value.strip()
                    # datetime
                    if "_at" in name:
                        if value != "":
                            tmp_dic[name] = datetime.strptime(
                                value, "%d %b %Y %H:%M")
                        else:
                            tmp_dic[name] = datetime.strptime(
                                "1000 01 01 00:00", "%Y %m %d %H:%M")
                    # int
                    elif name in {"created_by_id", "updated_by_id",
                                  "commented_by_id", "comments", "size",
                                  "rating_votes", "rating", "revisions"}:
                        if value != "":
                            tmp_dic[name] = int(value)
                        else:
                            tmp_dic[name] = 0
                    # tuple(tags)
                    elif name in {"tags", "_tags"}:
                        if value != "":
                            tmp_dic[name] = value.split(" ")
                        else:
                            tmp_dic[name] = []
                    # str
                    else:
                        tmp_dic[name] = value
                # null
                else:
                    tmp_dic[name] = ""

            # merge
            contents.update({tmp_dic[kwargs["main_key"]]: tmp_dic})

        return {
            "status": "success",
            "pages": {
                "current": currentpage,
                "total": totalpage
            },
            "contents": contents
        }

    def settag(self, url, pageid, tags):
        if self.acc_user != "unknown":
            try:
                body = {
                    "action": "WikiPageAction",
                    "event": "saveTags",
                    "moduleName": "Empty",
                    "tags": " ".join(tags),
                    "pageId": pageid
                }
                return self.ajaxcon(body=body, url=url)
            except AjaxError:
                raise ModuleError("Error occured while processing settag.")
        else:
            raise LoginError("You need to login to wikidot")

    def editpage(self, *, mode="edit", url, fullname,
                 pageid="", title="", content=""):
        if self.acc_user != "unknown":
            try:
                if mode == "edit":
                    getdata = self.ajaxcon(url=url,
                                           body={
                                               "mode": "page",
                                               "wiki_page": "start",
                                               "moduleName": "edit/PageEditModule",
                                               "page_id": pageid,
                                           })
                    if "locked" in getdata or "other_locks" in getdata:
                        confirm = input(
                            "Do you want to remove page-lock forcibly?(y/n)")
                        if confirm != "y":
                            return
                        getdata = self.ajaxcon(url=url,
                                               body={
                                                   "mode": "page",
                                                   "wiki_page": fullname,
                                                   "moduleName": "edit/PageEditModule",
                                                   "page_id": pageid,
                                                   "force_lock": "yes"
                                               })

                elif mode == "new":
                    getdata = {
                        "lock_id": "",
                        "lock_secret": "",
                        "page_revision_id": ""
                    }
                    pageid = ""

                body = {
                    "action": "WikiPageAction",
                    "event": "savePage",
                    "mode": "page",
                    "lock_id": getdata["lock_id"],
                    "lock_secret": getdata["lock_secret"],
                    "page_revision_id": getdata["page_revision_id"],
                    "wiki_page": fullname,
                    "moduleName": "Empty",
                    "page_id": pageid,
                    "title": title,
                    "source": content,
                    "comments": "ALICEによる自動編集"
                }
                return self.ajaxcon(body=body, url=url)
            except AjaxError:
                raise ModuleError("Error occured while processing editpage")
        else:
            raise LoginError("You need to login to wikidot")

    def getsource(self, url, pageid):
        try:
            body = {
                "wikidot_token7": "123456",
                "moduleName": "viewsource/ViewSourceModule",
                "page_id": pageid
            }
            json = self.ajaxcon(body=body, url=url)
            content = json["body"].replace("[[<]]", "[[|tmp_lt|]]").replace("[[/<]]", "[[|/tmp_gt|]]").replace("[[<]]", "[[|tmp_gt|]]").replace("[[/<]]", "[[|/tmp_gt|]]")
            content = bs4(content, 'lxml')
            content = content.find("div").get_text()
            content = content.replace("[[|tmp_lt|]]", "[[<]]").replace("[[|/tmp_gt|]]", "[[/<]]").replace("[[|tmp_gt|]]", "[[<]]").replace("[[|/tmp_gt|]]", "[[/<]]")
            return content.strip()
        except Exception:
            return

    def getthreadcategories(self, url, hidden=False):
        try:
            result = []
            body = {
                "wikidot_token7": "123456",
                "moduleName": "forum/ForumStartModule",
                "hidden": hidden
            }
            json = self.ajaxcon(body=body, url=url)
            content = html.unescape(json["body"])
            content = bs4(content, 'lxml')
            categories = content.find_all("td", class_="name")
            for category in categories:
                title = category.find("div", class_="title").find("a")
                catid = title["href"]
                catid = re.search(r'\d+', catid).group()
                catid = int(catid)
                catname = title.string
                result.append({"id": catid, "name": catname})
            return result
        except Exception:
            raise ModuleError("Error occured while processing tagset")

    def getforumthreads(self, url, categoryid):
        def _innerfunc(self, url, categoryid, page):
            try:
                result = {}

                body = {
                    "wikidot_token7": "123456",
                    "moduleName": "forum/ForumViewCategoryModule",
                    "c": categoryid,
                    "p": page
                }
                json = self.ajaxcon(body=body, url=url)
                content = html.unescape(json["body"])
                content = bs4(content, 'lxml')
                statistics = content.find("div", class_="statistics").get_text("::").split("::")
                num_threads = int(re.search(r'\d+', statistics[0]).group())
                num_pages = math.ceil(num_threads / 20)
                threads = content.find_all("tr", class_="")
                for thread in threads:
                    titleelem = thread.find("div", class_="title").find("a")
                    threadid = titleelem["href"]
                    threadid = int(re.search(r'\d+', threadid).group())
                    threadtitle = titleelem.string
                    startedelem = thread.find("td", class_="started")
                    startdate = startedelem.find("span", class_="odate").string
                    startdate = datetime.strptime(startdate, "%d %b %Y %H:%M")
                    author = startedelem.find("span", class_="printuser")
                    if author.find("a"):
                        author_data = author.find("a")
                        try:
                            author_unix = author_data["href"].replace("http://www.wikidot.com/user:info/", "")
                            author_id = author_data["onclick"].replace("WIKIDOT.page.listeners.userInfo(", "")
                            author_id = author_id.replace("); return false;", "")
                            author_id = int(author_id)
                        except Exception:
                            author_unix = "guest"
                            author_id = -2
                    elif author.string == "Wikidot":
                        author_unix = "wikidot"
                        author_id = -1
                    else:
                        author_unix = "unknown"
                        author_id = -3
                    posts = int(thread.find("td", class_="posts").string)
                    result.update({
                        threadid: {
                            "title": str(threadtitle),
                            "author_id": int(author_id),
                            "author_unix": str(author_unix),
                            "posts": int(posts),
                            "start": startdate
                        }
                    })
                return num_pages, result
            except Exception:
                raise ModuleError(
                    "Error occured while processing getforumthreads_inner")

        try:
            result = {}
            request = _innerfunc(self, url=url, categoryid=categoryid, page=1)
            pages = request[0]
            result.update(request[1])
            for i in range(2, pages + 1):
                request = _innerfunc(self, url=url, categoryid=categoryid, page=i)
                result.update(request[1])
            return result
        except Exception:
            raise ModuleError("Error occured while processing getforumthreads")

    def getnewpostspercategory(self, url, categoryid):
        try:
            result = []
            feed = feedparser.parse(
                f"http://{url}/feed/forum/cp-{categoryid}.xml")
            posts = feed.entries
            for post in posts:
                try:
                    guid = post.guid
                    guid = guid.replace(f"http://{url}/forum/t-", "")
                    guid = guid.split("#post-")
                    threadid = guid[0]
                    postid = guid[1]
                    title = post.title
                    try:
                        author = post.wikidot_authorname
                        author = author.lower()
                        author = re.sub("[_ ]", "-", author)
                    except Exception:
                        author = "unknown"
                    postdate = datetime.strptime(
                        post.published, "%a, %d %b %Y %H:%M:%S %z")
                    postdate = postdate.astimezone()
                    result.append({
                        "categoryid": categoryid,
                        "threadid": threadid,
                        "postid": postid,
                        "title": title,
                        "author": author,
                        "postdate": postdate
                    })
                except Exception:
                    raise
            return result
        except Exception:
            raise

    def getparentpageofperpagediscussion(self, url, threadid, forumcategoryname="forum"):
        try:
            res = requests.get(f"http://{url}/{forumcategoryname}/t-{threadid}")
            contents = bs4(res.text, 'lxml')
            fullname = contents.find("div", id="page-title").find("a")["href"]
            fullname = fullname.lstrip("/")
            return fullname

        except Exception:
            return None
