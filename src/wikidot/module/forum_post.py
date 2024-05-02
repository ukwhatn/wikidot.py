from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wikidot.module.page import Page
    from wikidot.module.user import AbstractUser
    from wikidot.module.site import Site
    from wikidot.module.forum_thread import ForumThread

class ForumPostCollection(list["ForumPost"]):
    def __init__(self, thread: "ForumThread", posts: list["ForumPost"]):
        super().__init__(posts)
        self.thread = thread

    def __iter__(self) -> Iterator["ForumPost"]:
        return super().__iter__()
    
    @staticmethod
    def _acquire_posts(thread: "ForumThread", posts: list["ForumPost"]):
        pass    #在这里继续

    def get_discuss_posts(self):
        return self._acquire_posts(self.page, self)

@dataclass
class ForumPost:
    page: "Page"
    user: "AbstractUser"