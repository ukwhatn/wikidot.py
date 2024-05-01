from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wikidot.module.page import Page
    from wikidot.module.user import AbstractUser
    from wikidot.module.site import Site
    from wikidot.module.forum_thread import ForumThread

class PostCollection(list["Post"]):
    def __init__(self, discuss: "ForumThread", Posts: list["Post"]):
        super().__init__(Posts)
        self.discuss = discuss
        self.page = discuss.page

    def __iter__(self) -> Iterator["Post"]:
        return super().__iter__()
    
    @staticmethod
    def _acquire_posts(discuss: "ForumThread", posts: list["Post"]):
        pass    #在这里继续

    def get_discuss_posts(self):
        return self._acquire_posts(self.page, self)

@dataclass
class Post:
    page: "Page"
    user: "AbstractUser"