from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from wikidot.module.forum_group import ForumGroup
    from wikidot.module.forum import Forum
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

    def get(self, id: int) -> Optional["ForumCategory"]:
        for category in self:
            if category.id == id:
                return category
    

@dataclass
class ForumCategory:
    site: "Site"
    id: int
    forum: "Forum"
    title: str
    description: str
    group: "ForumGroup" = None
    _threads_counts: int = None
    #_threads: list["ForumThread"] = None
    _posts_counts: int = None
    