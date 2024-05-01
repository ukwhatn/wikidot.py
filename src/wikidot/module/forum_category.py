from collections.abc import Iterator
from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup


if TYPE_CHECKING:
    from wikidot.module.forum_group import ForumGroup
    from wikidot.module.forum import Forum, ForumCategoryMethods
    from wikidot.module.site import Site


class ForumCategoryCollection(list["ForumCategory"]):
    def __init__(self, site: "Site" = None, category: list["ForumCategory"] = None):
        super().__init__(category or [])

        if site is not None:
            self.site = site
        else:
            self.site = self[0].site
    
    def __iter__(self) -> Iterator["ForumCategory"]:
        return super().__iter__()
    
    @staticmethod
    def _acquire_categories(site: "Site",forum: "Forum"):
        categories = []

        for group in forum.groups:
            categories.extend(group.categories)

        forum._categories = ForumCategoryCollection(site, categories)

    def find(self, id: int, get_while_not_found: bool = False) -> Optional["ForumCategory"]:
        for category in self:
            if category.id == id:
                category.update()
                return category
        if get_while_not_found:
            self.site.forum.category.get(id)


@dataclass
class ForumCategory:
    site: "Site"
    id: int
    forum: "Forum"
    title: str = None
    description: str = None
    group: "ForumGroup" = None
    threads_counts: int = None
    #_threads: list["ForumThread"] = None
    posts_counts: int = None
    
    def get_url(self):
        return f"{self.site.get_url}/forum/c-{self.id}"

    def update(self):
        response = self.site.amc_request(
            [
                {
                    "c": self.id,
                    "order": "",
                    "moduleName":"forum/ForumViewCategoryModule",
                }
            ]
        )[0]
        
        html = BeautifulSoup(response.json()["body"],"lxml")
        statistics = html.select_one("div.statistics").text
        info = html.select_one("div.forum-breadcrumbs").text

        self.title = html.select_one("div.page-title").text
        self.description = html.select_one("div.description-block well").text
        self.threads_counts, self.posts_counts = re.findall(r"\d+", statistics)
        self.group = self.forum.groups.find(re.search(r"(\S*) /\n\t+(\S*)", info).groups())
