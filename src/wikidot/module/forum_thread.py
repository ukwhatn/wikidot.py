from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING
from bs4 import BeautifulSoup

from wikidot.module.forum_post import PostCollection

if TYPE_CHECKING:
    from wikidot.module.page import Page
    from wikidot.module.user import AbstractUser
    from wikidot.module.site import Site

@dataclass
class ForumThread:
    def __init__(self, site: "Site", id: int) -> None:
        self.site = site
        self.id = id
        self.posts = None
        self.page: "Page" = None

        response = self.site.amc_request(
            [
                {
                    "t": self.id,
                    "order": "",
                    "moduleName":"forum/ForumViewThreadModule",
                }
            ]
        )[0]

        print(BeautifulSoup(response.json()['body'],'html.parser').find)
    
    def __str__(self):
        return f"Site({self.site}), id={self.id}, _posts={self.posts}"

    def get_url(self) -> str:
        return f"{self.site.get_url()}/forum/t-{self.id}"

    @property
    def posts(self) -> PostCollection:
        if self.posts is None:
            PostCollection(self.site, [self]).get_discuss_posts()
        return self.posts
    
    @posts.setter
    def posts(self, value: PostCollection):
        self.posts = value

    def update():
        pass #未完成