from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
import re
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
    from wikidot.module.user import AbstractUser
    from wikidot.module.site import Site

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
                {
                    "t": thread.id,
                    "moduleName": "forum/ForumViewThreadModule"
                }
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

            thread.title = re.search(r"» ([ \S]+)$", title).group(1)
            thread.category = thread.forum.category.get(int(category_id))
            if html.select_one("div.description-block div.head") is None:
                thread.description = ""
            else:
                description = html.select_one("div.description-block").text.strip()
                thread.description = re.search(r"[ \S]+$", description).group() 
            thread.posts_counts = int(re.findall(r"\n.+\D(\d+)", statistics.text)[-1])
            thread.created_by = user_parser(client, user)
            thread.created_at = odate_parser(odate)
            if (page_ele:=html.select_one("div.description-block>a")) is not None:
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
    last: "ForumPost" = None
    posts_counts: int = None
    page: "Page" = None

    @property
    def posts(self):
        response = self.site.amc_request(
            [
                {
                    "t": self.id,
                    "moduleName":"forum/ForumViewThreadModule",
                }
            ]
        )[0]

        #未完成

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
        
        self.site.amc_request(
            [
                {
                    "threadId": self.id,
                    "title": self.title if title is None else title,
                    "description": self.description if description is None else description,
                    "action": "ForumAction",
                    "event": "saveThreadMeta",
                    "moduleName": "Empty"
                }
            ]
        )

        if title is not None:
            self.title = title
        
        if description is not None:
            self.description = description

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
                    "moduleName": "Empty"
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
                    "moduleName": "Empty"
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
                    "moduleName": "Empty"
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
                    "moduleName": "forum/sub/ForumEditThreadBlockModule"
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
                    "moduleName": "Empty"
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
                    "moduleName": "Empty"
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
                    "moduleName": "forum/sub/ForumEditThreadStickinessModule"
                }
            ]
        )[0]

        html = BeautifulSoup(response.json()["body"], "lxml")
        checked = html.select_one("input.checkbox").get("checked")

        return checked is not None