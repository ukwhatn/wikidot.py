"""
Module for handling Wikidot forum post revisions (edit history)

This module provides classes and functions related to Wikidot forum post revisions.
It enables operations such as retrieving revision history and accessing historical content.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from .forum_post import ForumPost
    from .user import AbstractUser


class ForumPostRevisionCollection(list["ForumPostRevision"]):
    """
    Class representing a collection of forum post revisions

    A list extension class for storing and operating on multiple versions of a post's
    edit history (revisions) in bulk. Provides convenient functions such as
    batch retrieval of HTML content.
    """

    post: "ForumPost"

    def __init__(
        self,
        post: Optional["ForumPost"] = None,
        revisions: list["ForumPostRevision"] | None = None,
    ):
        """
        Initialize the collection

        Parameters
        ----------
        post : ForumPost | None, default None
            The post the revisions belong to. If None, inferred from the first revision
        revisions : list[ForumPostRevision] | None, default None
            List of revisions to store
        """
        super().__init__(revisions or [])
        if post is not None:
            self.post = post
        elif len(self) > 0:
            self.post = self[0].post

    def __iter__(self) -> Iterator["ForumPostRevision"]:
        """
        Return an iterator over the revisions in the collection

        Returns
        -------
        Iterator[ForumPostRevision]
            Iterator of revision objects
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["ForumPostRevision"]:
        """
        Get the revision with the specified ID

        Parameters
        ----------
        id : int
            The ID of the revision to retrieve

        Returns
        -------
        ForumPostRevision | None
            The revision with the specified ID, or None if not found
        """
        for revision in self:
            if revision.id == id:
                return revision
        return None

    def find_by_rev_no(self, rev_no: int) -> Optional["ForumPostRevision"]:
        """
        Get the revision with the specified revision number

        Parameters
        ----------
        rev_no : int
            The revision number to retrieve (0 = initial version)

        Returns
        -------
        ForumPostRevision | None
            The revision with the specified revision number, or None if not found
        """
        for revision in self:
            if revision.rev_no == rev_no:
                return revision
        return None

    @staticmethod
    def _parse(post: "ForumPost", html: BeautifulSoup) -> list["ForumPostRevision"]:
        """
        Parse revision list from HTML

        Parameters
        ----------
        post : ForumPost
            The post the revisions belong to
        html : BeautifulSoup
            HTML to parse

        Returns
        -------
        list[ForumPostRevision]
            List of parsed revisions (oldest first, with rev_no set)
        """
        revisions: list[ForumPostRevision] = []

        rows = html.select("table.table tr")
        for row in rows:
            # Skip header row
            row_class = row.get("class")
            if isinstance(row_class, list) and "head" in row_class:
                continue

            # Get user element
            user_elem = row.select_one("span.printuser")
            if user_elem is None:
                continue

            # Get odate element
            odate_elem = row.select_one("span.odate")
            if odate_elem is None:
                continue

            # Get revision ID from onclick attribute
            revision_link = row.select_one("a[onclick*='showRevision']")
            if revision_link is None:
                continue

            onclick = revision_link.get("onclick", "")
            match = re.search(r"showRevision\s*\(\s*event\s*,\s*(\d+)\s*\)", str(onclick))
            if match is None:
                continue

            revision_id = int(match.group(1))
            created_by = user_parser(post.thread.site.client, user_elem)
            created_at = odate_parser(odate_elem)

            revisions.append(
                ForumPostRevision(
                    post=post,
                    id=revision_id,
                    rev_no=0,  # Will be set after parsing all revisions
                    created_by=created_by,
                    created_at=created_at,
                )
            )

        # API returns newest first, reverse to get oldest first and set rev_no
        revisions.reverse()
        for i, revision in enumerate(revisions):
            # Use object.__setattr__ to set dataclass field
            object.__setattr__(revision, "rev_no", i)

        return revisions

    @staticmethod
    def acquire_all(post: "ForumPost") -> "ForumPostRevisionCollection":
        """
        Get all revisions for a post

        Parameters
        ----------
        post : ForumPost
            Forum post to get revisions for

        Returns
        -------
        ForumPostRevisionCollection
            Collection containing all revisions for the post
        """
        response = post.thread.site.amc_request(
            [
                {
                    "moduleName": "forum/sub/ForumPostRevisionsModule",
                    "postId": post.id,
                }
            ]
        )[0]

        body = response.json()["body"]
        html = BeautifulSoup(body, "lxml")

        revisions = ForumPostRevisionCollection._parse(post, html)
        return ForumPostRevisionCollection(post=post, revisions=revisions)

    @staticmethod
    def acquire_all_for_posts(
        posts: list["ForumPost"],
        with_html: bool = False,
    ) -> dict[int, "ForumPostRevisionCollection"]:
        """
        Get all revisions for multiple posts

        Batch retrieves revision history for the specified posts.
        Optionally retrieves HTML content for all revisions.

        Parameters
        ----------
        posts : list[ForumPost]
            List of posts to get revisions for
        with_html : bool, default False
            If True, also retrieves HTML content for all revisions

        Returns
        -------
        dict[int, ForumPostRevisionCollection]
            Dictionary mapping post ID to ForumPostRevisionCollection
        """
        if len(posts) == 0:
            return {}

        result: dict[int, ForumPostRevisionCollection] = {}
        site = posts[0].thread.site

        # Step 1: Get revision lists for all posts
        responses = site.amc_request(
            [
                {
                    "moduleName": "forum/sub/ForumPostRevisionsModule",
                    "postId": post.id,
                }
                for post in posts
            ]
        )

        # Step 2: Parse revision lists
        for post, response in zip(posts, responses, strict=True):
            body = response.json()["body"]
            html = BeautifulSoup(body, "lxml")
            revisions = ForumPostRevisionCollection._parse(post, html)
            result[post.id] = ForumPostRevisionCollection(post=post, revisions=revisions)

        # Step 3: Optionally get HTML content for all revisions
        if with_html:
            all_revisions: list[ForumPostRevision] = []
            for collection in result.values():
                for revision in collection:
                    if not revision.is_html_acquired():
                        all_revisions.append(revision)

            if len(all_revisions) > 0:
                html_responses = site.amc_request(
                    [
                        {
                            "moduleName": "forum/sub/ForumPostRevisionModule",
                            "revisionId": revision.id,
                        }
                        for revision in all_revisions
                    ]
                )

                for revision, response in zip(all_revisions, html_responses, strict=True):
                    data = response.json()
                    revision._html = str(data.get("content", ""))

        return result

    def get_htmls(self) -> "ForumPostRevisionCollection":
        """
        Get HTML content for all revisions in the collection

        Returns
        -------
        ForumPostRevisionCollection
            Self (for method chaining)
        """
        target_revisions = [r for r in self if not r.is_html_acquired()]

        if len(target_revisions) == 0:
            return self

        responses = self.post.thread.site.amc_request(
            [{"moduleName": "forum/sub/ForumPostRevisionModule", "revisionId": r.id} for r in target_revisions]
        )

        for revision, response in zip(target_revisions, responses, strict=True):
            data = response.json()
            revision._html = str(data.get("content", ""))

        return self


@dataclass
class ForumPostRevision:
    """
    Class representing a forum post revision (version in edit history)

    Holds information about a specific version of a post. Provides basic information
    such as revision number, creator, and creation date, along with access to HTML content.

    Attributes
    ----------
    post : ForumPost
        The post this revision belongs to
    id : int
        Revision ID
    rev_no : int
        Revision number (0 = initial version)
    created_by : AbstractUser
        The creator of the revision
    created_at : datetime
        The creation date and time of the revision
    _html : str | None, default None
        The revision's HTML content (internal cache)
    """

    post: "ForumPost"
    id: int
    rev_no: int
    created_by: "AbstractUser"
    created_at: datetime
    _html: str | None = None

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the revision
        """
        return f"ForumPostRevision(id={self.id}, rev_no={self.rev_no})"

    def is_html_acquired(self) -> bool:
        """
        Check if HTML content has already been acquired

        Returns
        -------
        bool
            True if HTML content is acquired, False otherwise
        """
        return self._html is not None

    @property
    def html(self) -> str | None:
        """
        Get the revision's HTML content

        Automatically fetches the HTML content if not yet acquired.

        Returns
        -------
        str | None
            The revision's HTML content
        """
        if not self.is_html_acquired():
            ForumPostRevisionCollection(self.post, [self]).get_htmls()
        return self._html

    @html.setter
    def html(self, value: str) -> None:
        """
        Set the revision's HTML content

        Parameters
        ----------
        value : str
            The HTML content to set
        """
        self._html = value
