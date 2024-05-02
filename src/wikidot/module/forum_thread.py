from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from bs4 import BeautifulSoup

from wikidot.module.forum_post import ForumPost, ForumPostCollection

if TYPE_CHECKING:
    from wikidot.module.forum import Forum
    from wikidot.module.forum_category import ForumCategory
    from wikidot.module.page import Page
    from wikidot.module.user import User
    from wikidot.module.site import Site

class ForumThreadCollection(list["ForumThread"]):
    def __init__(self, category: "ForumCategory", threads: list["ForumThread"] = None):
        super().__init__(threads or [])
        self.category = category
    
    def __iter__(self) -> Iterator["ForumThread"]:
        return super().__iter__()

@dataclass
class ForumThread:
    site: "Site"
    id: int
    forum: "Forum"
    category: "ForumCategory" = None
    title: str = None
    description: str = None
    created_by: "User" = None
    created_at: datetime = None
    last: "ForumPost" = None
    posts_counts: int = None
    page: "Page" = None

    @property
    def posts(self):
        response = self.site.amc_request(
            [
                {
                    "t": self.id,
                    "order": "",
                    "moduleName":"forum/ForumViewThreadModule",
                }
            ]
        )[0]

    def get_url(self) -> str:
        return f"{self.site.get_url()}/forum/t-{self.id}"

    @property
    def posts(self) -> ForumPostCollection:
        if self.posts is None:
            ForumPostCollection(self.site, [self]).get_discuss_posts()
        return self.posts

    @posts.setter
    def posts(self, value: ForumPostCollection):
        self.posts = value

    def update():
        pass #未完成