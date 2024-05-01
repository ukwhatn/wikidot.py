from dataclasses import dataclass
from typing import TYPE_CHECKING

from wikidot.module.forum_category import ForumCategory, ForumCategoryCollection
from wikidot.module.forum_group import ForumGroup, ForumGroupCollection

if TYPE_CHECKING:
    from wikidot.module.site import Site

@dataclass
class Forum:
    site: "Site"
    name = "Forum"
    _groups: "ForumGroupCollection" = None
    _categories: "ForumCategoryCollection" = None

    def get_url(self):
        return f"{self.site.get_url}/forum/start"

    @property
    def groups(self):
        if self._groups is None:
            ForumGroupCollection._acquire_groups(self.site, self)
        return self._groups

    @property
    def categories(self):
        if self._categories is None:
            ForumCategoryCollection._acquire_categories(self.site, self)
        return self._categories
