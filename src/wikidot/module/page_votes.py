"""
Module for handling Wikidot page votes (ratings)

This module provides classes and functions related to Wikidot page votes (ratings).
It enables operations such as retrieving and displaying vote information for pages.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .page import Page
    from .user import AbstractUser


class PageVoteCollection(list["PageVote"]):
    """
    Class representing a collection of page votes

    A list extension class for storing and operating on multiple votes (ratings)
    for a page in bulk.
    """

    page: "Page"

    def __init__(self, page: "Page", votes: list["PageVote"]):
        """
        Initialize the collection

        Parameters
        ----------
        page : Page
            The page the votes belong to
        votes : list[PageVote]
            List of votes to store
        """
        super().__init__(votes)
        self.page = page

    def __iter__(self) -> Iterator["PageVote"]:
        """
        Return an iterator over the votes in the collection

        Returns
        -------
        Iterator[PageVote]
            Iterator of vote objects
        """
        return super().__iter__()

    def find(self, user: "AbstractUser") -> "PageVote":
        """
        Get the vote by the specified user

        Parameters
        ----------
        user : AbstractUser
            The user who cast the vote

        Returns
        -------
        PageVote
            The user's vote information
        """
        for vote in self:
            if vote.user.id == user.id:
                return vote
        raise ValueError(f"User {user} has not voted on page {self.page}")


@dataclass
class PageVote:
    """
    Class representing a vote (rating) for a page

    Holds information about a vote (rating) cast by a user for a page.

    Attributes
    ----------
    page : Page
        The page the vote belongs to
    user : AbstractUser
        The user who cast the vote
    value : int
        The vote value (+1/-1 or numeric)
    """

    page: "Page"
    user: "AbstractUser"
    value: int
