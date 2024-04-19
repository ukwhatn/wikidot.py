from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wikidot.module.page import Page
    from wikidot.module.user import AbstractUser


class PageVoteCollection(list["PageVote"]):
    def __init__(self, page: "Page", votes: list["PageVote"]):
        super().__init__(votes)
        self.page = page

    def __iter__(self) -> Iterator["PageVote"]:
        return super().__iter__()


@dataclass
class PageVote:
    page: "Page"
    user: "AbstractUser"
    value: int
