import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from ..common.exceptions import NoElementException
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from .forum_category import ForumCategory
    from .site import Site
    from .user import AbstractUser


class ForumThreadCollection(list["ForumThread"]):
    def __init__(
        self,
        site: Optional["Site"] = None,
        threads: Optional[list["ForumThread"]] = None,
    ):
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
            if title is None:
                raise NoElementException("Title element is not found.")

            title_href = title.get("href")
            if title_href is None:
                raise NoElementException("Title href is not found.")

            thread_id_match = re.search(r"t-(\d+)", str(title_href))
            if thread_id_match is None:
                raise NoElementException("Thread ID is not found.")

            thread_id = int(thread_id_match.group(1))

            description_elem = info.select_one("div.description")
            user_elem = info.select_one("span.printuser")
            odate_elem = info.select_one("span.odate")
            posts_count_elem = info.select_one("td.posts")

            if description_elem is None:
                raise NoElementException("Description element is not found.")
            if user_elem is None:
                raise NoElementException("User element is not found.")
            if odate_elem is None:
                raise NoElementException("Odate element is not found.")
            if posts_count_elem is None:
                raise NoElementException("Posts count element is not found.")

            thread = ForumThread(
                category=category,
                id=int(thread_id),
                title=title.text,
                description=description_elem.text,
                created_by=user_parser(category.site.client, user_elem),
                created_at=odate_parser(odate_elem),
                post_count=int(posts_count_elem.text),
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
    category: "ForumCategory"
    id: int
    title: str
    description: str
    created_by: "AbstractUser"
    created_at: datetime
    post_count: int

    def __str__(self):
        return (
            f"ForumThread(id={self.id}, "
            f"title={self.title}, description={self.description}, "
            f"created_by={self.created_by}, created_at={self.created_at}, "
            f"post_count={self.post_count})"
        )
