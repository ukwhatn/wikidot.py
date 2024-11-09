import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from .forum_thread import ForumThreadCollection

if TYPE_CHECKING:
    from .site import Site


class ForumCategoryCollection(list["ForumCategory"]):
    def __init__(self, site: "Site" = None, categories: list["ForumCategory"] = None):
        super().__init__(categories or [])

        if site is not None:
            self.site = site
        else:
            self.site = self[0].site

    def __iter__(self) -> Iterator["ForumCategory"]:
        return super().__iter__()

    @staticmethod
    def acquire_all(site: "Site"):
        categories = []

        response = site.amc_request(
            [{"moduleName": "forum/ForumStartModule", "hidden": "true"}]
        )[0]

        body = response.json()["body"]
        html = BeautifulSoup(body, "lxml")

        for row in html.select("table tr.head~tr"):
            name = row.select_one("td.name")
            thread_count = int(row.select_one("td.threads").text)
            post_count = int(row.select_one("td.posts").text)

            category = ForumCategory(
                site=site,
                id=int(
                    re.search(r"c-(\d+)", name.select_one("a").get("href")).group(1)
                ),
                title=name.select_one("a").text,
                description=name.select_one("div.description").text,
                threads_count=thread_count,
                posts_count=post_count,
            )

            categories.append(category)

        return ForumCategoryCollection(site=site, categories=categories)


@dataclass
class ForumCategory:
    site: "Site"
    id: int
    title: str
    description: str
    threads_count: int
    posts_count: int
    _threads: ForumThreadCollection = None

    def __str__(self):
        return (
            f"ForumCategory(id={self.id}, "
            f"title={self.title}, description={self.description}, "
            f"threads_count={self.threads_count}, posts_count={self.posts_count})"
        )

    @property
    def threads(self) -> ForumThreadCollection:
        if self._threads is None:
            self._threads = ForumThreadCollection.acquire_all(self)
        return self._threads

    @threads.setter
    def threads(self, value):
        self._threads = value

    def reload_threads(self):
        self._threads = ForumThreadCollection.acquire_all(self)
        return self._threads
