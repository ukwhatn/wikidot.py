import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from wikidot.common import exceptions
from wikidot.module.forum_post import ForumPost, ForumPostCollection
from wikidot.util.parser import odate as odate_parser
from wikidot.util.parser import user as user_parser

if TYPE_CHECKING:
    from wikidot.module.forum import Forum
    from wikidot.module.forum_category import ForumCategory
    from wikidot.module.page import Page
    from wikidot.module.site import Site
    from wikidot.module.user import AbstractUser


class ForumThreadCollection(list["ForumThread"]):
    def __init__(self, forum: "Forum", threads: list["ForumThread"] = None):
        super().__init__(threads or [])
        self.forum = forum

    def __iter__(self) -> Iterator["ForumThread"]:
        return super().__iter__()

    def _acquire_update(forum: "Forum", threads: list["ForumThread"]):
        if len(threads) == 0:
            return threads

        client = forum.site.client
        responses = forum.site.amc_request(
            [
                {"t": thread.id, "moduleName": "forum/ForumViewThreadModule"}
                for thread in threads
            ]
        )

        for thread, response in zip(threads, responses):
            html = BeautifulSoup(response.json()["body"], "lxml")
            statistics = html.select_one("div.statistics")
            user = statistics.select_one("span.printuser")
            odate = statistics.select_one("span.odate")
            category_url = html.select("div.forum-breadcrumbs a")[1].get("href")
            category_id = re.search(r"c-(\d+)", category_url).group(1)
            title = html.select_one("div.forum-breadcrumbs").text.strip()
            counts = int(re.findall(r"\n.+\D(\d+)", statistics.text)[-1])

            thread.title = re.search(r"»([ \S]*)$", title).group(1).strip()
            thread.category = thread.forum.category.get(int(category_id))
            if html.select_one("div.description-block div.head") is None:
                thread.description = ""
            else:
                description = html.select_one("div.description-block").text.strip()
                thread.description = re.search(r"[ \S]+$", description).group()
            if thread.posts_counts != counts:
                thread.last = None
            thread.posts_counts = counts
            thread.created_by = user_parser(client, user)
            thread.created_at = odate_parser(odate)
            if (pagerno := html.select_one("span.pager-no")) is None:
                thread.pagerno = 1
            else:
                thread.pagerno = int(re.search(r"of (\d+)", pagerno.text).group(1))
            if (page_ele := html.select_one("div.description-block>a")) is not None:
                thread.page = thread.site.page.get(page_ele.get("href")[1:])
                thread.page.discuss = thread

        return threads

    def update(self):
        return ForumThreadCollection._acquire_update(self.forum, self)


@dataclass
class ForumThread:
    site: "Site"
    id: int
    forum: "Forum"
    category: "ForumCategory" = None
    title: str = None
    description: str = None
    created_by: "AbstractUser" = None
    created_at: datetime = None
    posts_counts: int = None
    page: "Page" = None
    pagerno: int = None
    _last_post_id: int = None
    _last: "ForumPost" = None

    @property
    def last(self):
        if self._last_post_id is not None:
            if self._last is None:
                self.update()
                self._last = self.get(self._last_post_id)
            return self._last

    @last.setter
    def last(self, value: "ForumPost"):
        self._last = value

    @property
    def posts(self) -> ForumPostCollection:
        client = self.site.client
        responses = self.site.amc_request(
            [
                {
                    "pagerNo": no + 1,
                    "t": self.id,
                    "order": "",
                    "moduleName": "forum/ForumViewThreadPostsModule",
                }
                for no in range(self.pagerno)
            ]
        )

        posts = []

        for response in responses:
            html = BeautifulSoup(response.json()["body"], "lxml")
            for post in html.select("div.post"):
                cuser = post.select_one("div.info span.printuser")
                codate = post.select_one("div.info span.odate")
                if (parent := post.parent.get("id")) != "thread-container-posts":
                    parent_id = int(re.search(r"fpc-(\d+)", parent).group(1))
                else:
                    parent_id = None
                euser = post.select_one("div.changes span.printuser")
                eodate = post.select_one("div.changes span.odate a")

                posts.append(
                    ForumPost(
                        site=self.site,
                        id=int(re.search(r"post-(\d+)", post.get("id")).group(1)),
                        forum=self.forum,
                        thread=self,
                        _title=post.select_one("div.title").text.strip(),
                        parent_id=parent_id,
                        created_by=user_parser(client, cuser),
                        created_at=odate_parser(codate),
                        edited_by=(
                            client.user.get(euser.text) if euser is not None else None
                        ),
                        edited_at=odate_parser(eodate) if eodate is not None else None,
                        source_ele=post.select_one("div.content"),
                        source_text=post.select_one("div.content").text.strip(),
                    )
                )

        return ForumPostCollection(self, posts)

    def get_url(self) -> str:
        return f"{self.site.get_url()}/forum/t-{self.id}"

    def update(self) -> "ForumThread":
        return ForumThreadCollection(self.forum, [self]).update()[0]

    def edit(self, title: str = None, description: str = None):
        self.site.client.login_check()
        if title == "":
            raise exceptions.UnexpectedException("Title can not be left empty.")

        if self.page is not None:
            raise exceptions.UnexpectedException("Page's discussion can not be edited.")

        if title is None and description is None:
            return self

        self.site.amc_request(
            [
                {
                    "threadId": self.id,
                    "title": self.title if title is None else title,
                    "description": (
                        self.description if description is None else description
                    ),
                    "action": "ForumAction",
                    "event": "saveThreadMeta",
                    "moduleName": "Empty",
                }
            ]
        )

        self.title = self.title if title is None else title
        self.description = self.description if description is None else description

        return self

    def move_to(self, category_id: int):
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "categoryId": category_id,
                    "threadId": self.id,
                    "action": "ForumAction",
                    "event": "moveThread",
                    "moduleName": "Empty",
                }
            ]
        )

    def lock(self):
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "threadId": self.id,
                    "block": "true",
                    "action": "ForumAction",
                    "event": "saveBlock",
                    "moduleName": "Empty",
                }
            ]
        )

        return self

    def unlock(self):
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "threadId": self.id,
                    "action": "ForumAction",
                    "event": "saveBlock",
                    "moduleName": "Empty",
                }
            ]
        )

        return self

    def is_locked(self):
        self.site.client.login_check()
        response = self.site.amc_request(
            [
                {
                    "threadId": self.id,
                    "moduleName": "forum/sub/ForumEditThreadBlockModule",
                }
            ]
        )[0]

        html = BeautifulSoup(response.json()["body"], "lxml")
        checked = html.select_one("input.checkbox").get("checked")

        return checked is not None

    def stick(self):
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "threadId": self.id,
                    "sticky": "true",
                    "action": "ForumAction",
                    "event": "saveSticky",
                    "moduleName": "Empty",
                }
            ]
        )

        return self

    def unstick(self):
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "threadId": self.id,
                    "action": "ForumAction",
                    "event": "saveSticky",
                    "moduleName": "Empty",
                }
            ]
        )

        return self

    def is_sticked(self):
        self.site.client.login_check()
        response = self.site.amc_request(
            [
                {
                    "threadId": self.id,
                    "moduleName": "forum/sub/ForumEditThreadStickinessModule",
                }
            ]
        )[0]

        html = BeautifulSoup(response.json()["body"], "lxml")
        checked = html.select_one("input.checkbox").get("checked")

        return checked is not None

    def new_post(self, title: str = "", source: str = "", parent_id: int = ""):
        client = self.site.client
        client.login_check()
        if source == "":
            raise exceptions.UnexpectedException("Post body can not be left empty.")

        response = self.site.amc_request(
            [
                {
                    "parentId": parent_id,
                    "title": title,
                    "source": source,
                    "action": "ForumAction",
                    "event": "savePost",
                }
            ]
        )
        body = response.json()

        return ForumPost(
            site=self.site,
            id=int(body["postId"]),
            forum=self.forum,
            title=title,
            source=source,
            thread=self,
            parent_id=parent_id if parent_id == "" else None,
            created_by=client.user.get(client.username),
            created_at=datetime.fromtimestamp(body["CURRENT_TIMESTAMP"]),
        )

    def get(self, post_id: int):
        return self.posts.find(post_id)
