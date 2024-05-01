from dataclasses import dataclass
from typing import TYPE_CHECKING

from wikidot.module.forum_category import ForumCategory, ForumCategoryCollection
from wikidot.module.forum_group import ForumGroupCollection

if TYPE_CHECKING:
    from wikidot.module.site import Site

class ForumCategoryMethods:
    def __init__(self, forum: "Forum") -> None:
        self.forum = forum
        
    def get(self, id: int):
        category = ForumCategory(
                site = self.forum.site,
                id = id,
                forum = self.forum,
            )
        category.update()
        return category

@dataclass
class Forum:
    site: "Site"
    name = "Forum"
    _groups: "ForumGroupCollection" = None
    _categories: "ForumCategoryCollection" = None

    def get_url(self):
        return f"{self.site.get_url}/forum/start"

    def __post_init__(self):
        self.category = ForumCategoryMethods(self)

    @property
    def groups(self):
        ForumGroupCollection._acquire_groups(self.site, self)
        return self._groups
    
    @groups.setter
    def groups(self, value: "ForumGroupCollection"):
        self._groups = value

    @property
    def categories(self):
        ForumCategoryCollection._acquire_categories(self.site, self)
        return self._categories

    @categories.setter
    def categories(self, value: "ForumCategoryCollection"):
        self._categories = value