from dataclasses import dataclass
from typing import TYPE_CHECKING

from wikidot.module.forum_category import ForumCategory, ForumCategoryCollection
from wikidot.module.forum_group import ForumGroupCollection
from wikidot.module.forum_thread import ForumThread

if TYPE_CHECKING:
    from wikidot.module.site import Site


class ForumCategoryMethods:
    def __init__(self, forum: "Forum") -> None:
        self.forum = forum

    def get(self, id: int):
        category = ForumCategory(
            site=self.forum.site,
            id=id,
            forum=self.forum,
        )
        return category.update()


class ForumThreadMethods:
    def __init__(self, forum: "Forum") -> None:
        self.forum = forum

    def get(self, id: int):
        thread = ForumThread(
            site=self.forum.site,
            id=id,
            forum=self.forum,
        )
        return thread.update()


@dataclass
class Forum:
    site: "Site"
    name = "Forum"
    _groups: "ForumGroupCollection" = None
    _categories: "ForumCategoryCollection" = None

    def __post_init__(self):
        self.category = ForumCategoryMethods(self)
        self.thread = ForumThreadMethods(self)

    def get_url(self):
        return f"{self.site.get_url}/forum/start"

    @property
    def groups(self):
        if self._groups is None:
            ForumGroupCollection.get_groups(self.site, self)
        return self._groups

    @property
    def categories(self):
        if self._categories is None:
            ForumCategoryCollection.get_categories(self.site, self)
        return self._categories
