import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from wikidot.util.parser import odate as odate_parser
from wikidot.util.parser import user as user_parser

if TYPE_CHECKING:
    from wikidot.module.forum_category import ForumCategory
    from wikidot.module.site import Site
    from wikidot.module.user import AbstractUser


class ForumThreadCollection(list["ForumThread"]):
    def __init__(self, site: "Site" = None, threads: list["ForumThread"] = None):
        super().__init__(threads or [])

        if site is not None:
            self.site = site
        else:
            self.site = self[0].category.site

    def __iter__(self) -> Iterator["ForumThread"]:
        return super().__iter__()

    @staticmethod
    def _parse(category: "ForumCategory", html: BeautifulSoup) -> list["ForumThread"]:
        threads = []
        for info in html.select("table.table tr.head~tr"):
            title = info.select_one("div.title a")
            thread_id = re.search(r"t-(\d+)", title.get("href")).group(1)
            description = info.select_one("div.description")
            user = info.select_one("span.printuser")
            odate = info.select_one("span.odate")
            posts_count = info.select_one("td.posts")

            thread = ForumThread(
                _category=category,
                id=int(thread_id),
                title=title.text,
                description=description.text,
                created_by=user_parser(category.site.client, user),
                created_at=odate_parser(odate),
                post_count=int(posts_count.text),
            )

            threads.append(thread)

        return threads

    @staticmethod
    def acquire_all(category: "ForumCategory") -> "ForumThreadCollection":
        threads = []

        first_response = category.site.amc_request(
            [
                {
                    "p": 1,
                    "c": category.id,
                    "moduleName": "forum/ForumViewCategoryModule",
                }
            ]
        )[0]

        first_body = first_response.json()["body"]
        first_html = BeautifulSoup(first_body, "lxml")

        threads.extend(ForumThreadCollection._parse(category, first_html))

        # pager検索
        pager = first_html.select_one("div.pager")
        if pager is None:
            return ForumThreadCollection(site=category.site, threads=threads)

        last_page = int(pager.select("a")[-2].text)
        if last_page == 1:
            return ForumThreadCollection(site=category.site, threads=threads)

        responses = category.site.amc_request(
            [
                {
                    "p": page,
                    "c": category.id,
                    "moduleName": "forum/ForumViewCategoryModule",
                }
                for page in range(2, last_page + 1)
            ]
        )

        for response in responses:
            body = response.json()["body"]
            html = BeautifulSoup(body, "lxml")
            threads.extend(ForumThreadCollection._parse(category, html))

        return ForumThreadCollection(site=category.site, threads=threads)


@dataclass
class ForumThread:
    id: int
    title: str
    description: str
    created_by: "AbstractUser"
    created_at: datetime
    post_count: int
    _category: Optional["ForumCategory"] = None

    def __str__(self):
        return (
            f"ForumThread(id={self.id}, "
            f"title={self.title}, description={self.description}, "
            f"created_by={self.created_by}, created_at={self.created_at}, "
            f"post_count={self.post_count})"
        )
