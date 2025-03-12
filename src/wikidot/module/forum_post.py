from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from .forum_thread import ForumThread
    from .user import AbstractUser


class ForumPostCollection(list["ForumPost"]):
    def __init__(
        self,
        thread: Optional["ForumThread"] = None,
        posts: Optional[list["ForumPost"]] = None,
    ):
        super().__init__(posts or [])

        if thread is not None:
            self.thread = thread
        else:
            self.thread = self[0].thread

    def __iter__(self) -> Iterator["ForumPost"]:
        return super().__iter__()

    # @staticmethod
    # def _parse(thread: "ForumThread", html: BeautifulSoup) -> list["ForumPost"]:
    #     pass


@dataclass
class ForumPost:
    thread: "ForumThread"
    id: int
    title: str
    text: str
    element: BeautifulSoup
    created_by: "AbstractUser"
    created_at: datetime
    edited_by: Optional["AbstractUser"] = None
    edited_at: Optional[datetime] = None
    _parent: Optional["ForumPost"] = None
    _source: Optional[str] = None

    def __str__(self):
        return (
            f"ForumPost(thread={self.thread}, id={self.id}, title={self.title}, "
            f"text={self.text}, created_by={self.created_by}, created_at={self.created_at}, "
            f"edited_by={self.edited_by}, edited_at={self.edited_at})"
        )
