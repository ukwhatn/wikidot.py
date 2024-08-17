import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from wikidot.module.forum_post import ForumPost
from wikidot.module.forum_thread import ForumThread, ForumThreadCollection
from wikidot.util.parser import odate as odate_parser
from wikidot.util.parser import user as user_parser

if TYPE_CHECKING:
    from wikidot.module.forum import Forum
    from wikidot.module.forum_group import ForumGroup
    from wikidot.module.site import Site


class ForumCategoryCollection(list["ForumCategory"]):
    def __init__(self, forum: "Forum", categories: list["ForumCategory"]):
        super().__init__(categories)
        self.forum = forum

    def __iter__(self) -> Iterator["ForumCategory"]:
        return super().__iter__()

    @staticmethod
    def get_categories(site: "Site", forum: "Forum"):
        categories = []

        for group in forum.groups:
            categories.extend(group.categories)

        forum._categories = ForumCategoryCollection(site, categories)

    def find(self, id: int = None, title: str = None) -> Optional["ForumCategory"]:
        for category in self:
            if (id is None or category.id == id) and (
                title is None or category.title
            ) == title:
                return category

    @staticmethod
    def _acquire_update(forum: "Forum", categories: list["ForumCategory"]):
        if len(categories) == 0:
            return categories

        responses = forum.site.amc_request(
            [
                {
                    "c": category.id,
                    "moduleName": "forum/ForumViewCategoryModule",
                }
                for category in categories
            ]
        )
        for category, response in zip(categories, responses):
            html = BeautifulSoup(response.json()["body"], "lxml")
            statistics = html.select_one("div.statistics").text
            description = html.select_one("div.description-block").text.strip()
            info = re.search(
                r"([ \S]*) /\s+([ \S]*)", html.select_one("div.forum-breadcrumbs").text
            )
            counts = re.findall(r"\d+", statistics)

            if category.posts_counts != int(counts[1]):
                category.last = None
            category.description = re.search(r"[ \S]*$", description).group()
            category.threads_counts, category.posts_counts = counts
            category.group = category.forum.groups.find(info.group(1))
            category.title = info.group(2)
            if (pagerno := html.select_one("span.pager-no")) is None:
                category.pagerno = 1
            else:
                category.pagerno = int(re.search(r"of (\d+)", pagerno.text).group(1))

        return categories

    def update(self):
        return ForumCategoryCollection._acquire_update(self.forum, self)


@dataclass
class ForumCategory:
    site: "Site"
    id: int
    forum: "Forum"
    title: str = None
    description: str = None
    group: "ForumGroup" = None
    threads_counts: int = None
    posts_counts: int = None
    pagerno: int = None
    _last_thread_id: int = None
    _last_post_id: int = None
    _last: "ForumPost" = None

    def get_url(self):
        return f"{self.site.get_url}/forum/c-{self.id}"

    def update(self):
        return ForumCategoryCollection(self.forum, [self]).update()[0]

    @property
    def last(self):
        if self._last_thread_id is not None and self._last_post_id is not None:
            if self._last is None:
                self._last = self.forum.thread.get(self._last_thread_id).get(
                    self._last_post_id
                )
            return self._last

    @last.setter
    def last(self, value: "ForumPost"):
        self._last = value

    @property
    def threads(self):
        client = self.site.client
        self.update()
        responses = self.site.amc_request(
            [
                {
                    "p": no + 1,
                    "c": self.id,
                    "moduleName": "forum/ForumViewCategoryModule",
                }
                for no in range(self.pagerno)
            ]
        )

        threads = []

        for response in responses:
            html = BeautifulSoup(response.json()["body"], "lxml")
            for info in html.select("table.table tr.head~tr"):
                title = info.select_one("div.title a")
                thread_id = re.search(r"t-(\d+)", title.get("href")).group(1)
                description = info.select_one("div.description")
                user = info.select_one("span.printuser")
                odate = info.select_one("span.odate")
                posts_count = info.select_one("td.posts")
                last_id = info.select_one("td.last>a")
                if last_id is None:
                    post_id = None
                else:
                    post_id = int(
                        re.search(r"post-(\d+)", last_id.get("href")).group(1)
                    )

                thread = ForumThread(
                    site=self.site,
                    id=thread_id,
                    forum=self.forum,
                    title=title.text,
                    description=description.text.strip(),
                    created_by=user_parser(client, user),
                    created_at=odate_parser(odate),
                    posts_counts=int(posts_count.text),
                    _last_post_id=post_id,
                )

                threads.append(thread)

        return ForumThreadCollection(self, threads)

    def new_thread(self, title: str, source: str, description: str = ""):
        client = self.site.client
        client.login_check()

        response = self.site.amc_request(
            [
                {
                    "category_id": self.id,
                    "title": title,
                    "description": description,
                    "source": source,
                    "action": "ForumAction",
                    "event": "newThread",
                }
            ]
        )[0]

        body = response.json()

        return ForumThread(
            site=self.site,
            id=body["threadId"],
            forum=self.forum,
            category=self,
            title=title,
            description=description,
            created_by=client.user.get(client.username),
            created_at=datetime.fromtimestamp(body["CURRENT_TIMESTAMP"]),
            posts_counts=1,
        )
