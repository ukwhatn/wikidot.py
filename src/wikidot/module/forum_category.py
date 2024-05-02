from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
import re
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from wikidot.module.forum_post import ForumPost
from wikidot.module.forum_thread import ForumThread, ForumThreadCollection
from wikidot.util.parser import odate as odate_parser
from wikidot.util.parser import user as user_parser

if TYPE_CHECKING:
    from wikidot.module.forum_group import ForumGroup
    from wikidot.module.forum import Forum
    from wikidot.module.site import Site


class ForumCategoryCollection(list["ForumCategory"]):
    def __init__(self, forum: "Forum", categories: list["ForumCategory"]):
        super().__init__(categories)
        self.forum = forum
    
    def __iter__(self) -> Iterator["ForumCategory"]:
        return super().__iter__()
    
    @staticmethod
    def _acquire_categories(site: "Site",forum: "Forum"):
        categories = []

        for group in forum.groups:
            categories.extend(group.categories)

        forum._categories = ForumCategoryCollection(site, categories)

    def find(self, id: int = None, title: str = None) -> Optional["ForumCategory"]:
        for category in self:
            if ((id is None or category.id == id) and
                (title is None or category.title) == title):
                return category


@dataclass
class ForumCategory:
    site: "Site"
    id: int
    forum: "Forum"
    title: str = None
    description: str = None
    group: "ForumGroup" = None
    last: "ForumPost" = None
    threads_counts: int = None
    posts_counts: int = None
    pagerno: int = None
    
    def get_url(self):
        return f"{self.site.get_url}/forum/c-{self.id}"

    def update(self):
        response = self.site.amc_request(
            [
                {
                    "c": self.id,
                    "moduleName":"forum/ForumViewCategoryModule",
                }
            ]
        )[0]
        
        html = BeautifulSoup(response.json()["body"], "lxml")
        statistics = html.select_one("div.statistics").text
        info = re.search(r"(\S*) /\s+(\S*)", html.select_one("div.forum-breadcrumbs").text)


        if self.posts_counts != re.findall(r"\d+", statistics)[1]:
            self.last = None
        self.description = re.search(r"\S*\s+$",html.select_one("div.description-block").text).group().strip()
        self.threads_counts, self.posts_counts = re.findall(r"\d+", statistics)
        self.group = self.forum.groups.find(info.group(1))
        self.title = info.group(2)
        if (pagerno:=html.select_one("span.pager-no")) is None:
            self.pagerno = 1
        else:
            self.pagerno = int(re.search(r"of (\d+)", pagerno.text).group(1))

    @property
    def threads(self):
        client = self.site.client
        self.update()
        responses = self.site.amc_request(
            [
                {
                    "p": no+1,
                    "c": self.id,
                    "moduleName":"forum/ForumViewCategoryModule",
                }
                for no in range(self.pagerno)
            ]
        )

        threads = []

        for response in responses:
            html = BeautifulSoup(response.json()["body"],"lxml")
            for info in html.select("table.table tr.head~tr"):
                title = info.select_one("div.title a")
                description = info.select_one("div.description")
                user = info.select_one("span.printuser")
                odate = info.select_one("span.odate")
                posts_count = info.select_one("td.posts")

                thread = ForumThread(
                    site=self.site,
                    id=re.search(r"t-(\d+)",title.get("href")).group(1),
                    forum=self.forum,
                    title=title.text,
                    description=description.text.strip(),
                    created_by=client.user.get(user_parser(client, user).unix_name),
                    created_at=odate_parser(odate),
                    posts_counts=int(posts_count.text)
                )

                threads.append(thread)

        return ForumThreadCollection(self, threads)
    
    def new_thread(self, title: str, source :str, description: str = ""):
        client = self.site.client

        response = self.site.amc_request(
            [
                {
                    "category_id": self.id,
                    "title": title,
                    "description": description,
                    "source": source,
                    "action": "ForumAction",
                    "event": "newThread"
                }
            ]
        )[0]

        return ForumThread(
            site=self.site,
            id=response.json()["threadId"],
            forum=self.forum,
            category=self,
            title=title,
            description=description,
            created_by=client.user.get(client.username),
            created_at=datetime.fromtimestamp(response.json()["CURRENT_TIMESTAMP"]),
            posts_counts=1
            )
