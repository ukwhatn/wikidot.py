"""
Module for handling Wikidot page edit history (revisions)

This module provides classes and functions related to Wikidot page edit history (revisions).
It enables operations such as retrieving revisions, getting source code, and displaying HTML.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import httpx
from bs4 import BeautifulSoup

from ..common.exceptions import NoElementException
from .page_source import PageSource

if TYPE_CHECKING:
    from .page import Page
    from .user import AbstractUser


class PageRevisionCollection(list["PageRevision"]):
    """
    Class representing a collection of page revisions

    A list extension class for storing and operating on multiple versions of a page's
    edit history (revisions) in bulk. Provides convenient functions such as
    batch retrieval of source code and HTML.
    """

    page: "Page | None"

    def __init__(
        self,
        page: Optional["Page"] = None,
        revisions: list["PageRevision"] | None = None,
    ):
        """
        Initialize the collection

        Parameters
        ----------
        page : Page | None, default None
            The page the revisions belong to. If None, inferred from the first revision
        revisions : list[PageRevision] | None, default None
            List of revisions to store
        """
        super().__init__(revisions or [])
        self.page = page or self[0].page if len(self) > 0 else None

    def __iter__(self) -> Iterator["PageRevision"]:
        """
        Return an iterator over the revisions in the collection

        Returns
        -------
        Iterator[PageRevision]
            Iterator of revision objects
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["PageRevision"]:
        """
        Get the revision with the specified ID

        Parameters
        ----------
        id : int
            The ID of the revision to retrieve

        Returns
        -------
        PageRevision | None
            The revision with the specified ID, or None if not found
        """
        for revision in self:
            if revision.id == id:
                return revision
        return None

    @staticmethod
    def _generic_acquire(
        page: "Page",
        revisions: list["PageRevision"],
        check_acquired_func: Callable[["PageRevision"], bool],
        module_name: str,
        process_response_func: Callable[["PageRevision", httpx.Response, "Page"], None],
    ) -> list["PageRevision"]:
        """
        Generic method for batch retrieval of revision data

        Parameters
        ----------
        page : Page
            The page the revisions belong to
        revisions : list[PageRevision]
            List of revisions to retrieve data for
        check_acquired_func : callable
            Function to check if data is already acquired
        module_name : str
            Module name to use in AMC request
        process_response_func : callable
            Function to process the response (revision, response, page) -> None

        Returns
        -------
        list[PageRevision]
            List of revisions with updated data
        """
        target_revisions = [revision for revision in revisions if not check_acquired_func(revision)]

        if len(target_revisions) == 0:
            return revisions

        responses = page.site.amc_request(
            [{"moduleName": module_name, "revision_id": revision.id} for revision in target_revisions]
        )

        for revision, response in zip(target_revisions, responses, strict=True):
            process_response_func(revision, response, page)

        return revisions

    @staticmethod
    def _acquire_sources(page: "Page", revisions: list["PageRevision"]) -> list["PageRevision"]:
        """
        Internal method to batch retrieve source code for multiple revisions

        Requests and retrieves source code for revisions that haven't been fetched yet.

        Parameters
        ----------
        page : Page
            The page the revisions belong to
        revisions : list[PageRevision]
            List of revisions to retrieve source code for

        Returns
        -------
        list[PageRevision]
            List of revisions with updated source code information

        Raises
        ------
        NoElementException
            If source element is not found
        """

        def process_source_response(revision: "PageRevision", response: httpx.Response, page: "Page") -> None:
            body = response.json()["body"]
            # Replace nbsp with space
            body = body.replace("&nbsp;", " ")
            body_html = BeautifulSoup(body, "lxml")
            wiki_text_elem = body_html.select_one("div.page-source")
            if wiki_text_elem is None:
                raise NoElementException("Wiki text element not found")
            revision.source = PageSource(
                page=page,
                wiki_text=wiki_text_elem.get_text().strip(),
            )

        return PageRevisionCollection._generic_acquire(
            page,
            revisions,
            lambda r: r.is_source_acquired(),
            "history/PageSourceModule",
            process_source_response,
        )

    def get_sources(self) -> "PageRevisionCollection":
        """
        Get source code for all revisions in the collection

        Returns
        -------
        PageRevisionCollection
            Self (for method chaining)
        """
        if self.page is None:
            raise ValueError("Page is not set for this collection")
        self._acquire_sources(self.page, self)
        return self

    @staticmethod
    def _acquire_htmls(page: "Page", revisions: list["PageRevision"]) -> list["PageRevision"]:
        """
        Internal method to batch retrieve HTML display for multiple revisions

        Requests and retrieves HTML for revisions that haven't been fetched yet.

        Parameters
        ----------
        page : Page
            The page the revisions belong to
        revisions : list[PageRevision]
            List of revisions to retrieve HTML for

        Returns
        -------
        list[PageRevision]
            List of revisions with updated HTML information
        """

        def process_html_response(revision: "PageRevision", response: httpx.Response, page: "Page") -> None:
            body = response.json()["body"]
            # onclick="document.getElementById('page-version-info').style.display='none'">(.*?)</a>\n\t</div>\n\n\n\n
            # 以降をソースとして取得
            source = body.split(
                "onclick=\"document.getElementById('page-version-info').style.display='none'\">",
                maxsplit=1,
            )[1]
            source = source.split("</a>\n\t</div>\n\n\n\n", maxsplit=1)[1]
            revision._html = source

        return PageRevisionCollection._generic_acquire(
            page,
            revisions,
            lambda r: r.is_html_acquired(),
            "history/PageVersionModule",
            process_html_response,
        )

    def get_htmls(self) -> "PageRevisionCollection":
        """
        Get HTML display for all revisions in the collection

        Returns
        -------
        PageRevisionCollection
            Self (for method chaining)
        """
        if self.page is None:
            raise ValueError("Page is not set for this collection")
        self._acquire_htmls(self.page, self)
        return self


@dataclass
class PageRevision:
    """
    Class representing a page revision (version in edit history)

    Holds information about a specific version of a page. Provides basic information
    such as revision number, creator, creation date, and edit comment, along with
    access to source code and HTML display.

    Attributes
    ----------
    page : Page
        The page this revision belongs to
    id : int
        Revision ID
    rev_no : int
        Revision number
    created_by : AbstractUser
        The creator of the revision
    created_at : datetime
        The creation date and time of the revision
    comment : str
        Edit comment
    _source : PageSource | None, default None
        The revision's source code (internal cache)
    _html : str | None, default None
        The revision's HTML display (internal cache)
    """

    page: "Page"
    id: int
    rev_no: int
    created_by: "AbstractUser"
    created_at: datetime
    comment: str
    _source: Optional["PageSource"] = None
    _html: str | None = None

    def is_source_acquired(self) -> bool:
        """
        Check if source code has already been acquired

        Returns
        -------
        bool
            True if source code is acquired, False otherwise
        """
        return self._source is not None

    def is_html_acquired(self) -> bool:
        """
        Check if HTML display has already been acquired

        Returns
        -------
        bool
            True if HTML display is acquired, False otherwise
        """
        return self._html is not None

    @property
    def source(self) -> Optional["PageSource"]:
        """
        Get the revision's source code

        Automatically fetches the source code if not yet acquired.

        Returns
        -------
        PageSource | None
            The revision's source code
        """
        if not self.is_source_acquired():
            PageRevisionCollection(self.page, [self]).get_sources()
        return self._source

    @source.setter
    def source(self, value: "PageSource") -> None:
        """
        Set the revision's source code

        Parameters
        ----------
        value : PageSource
            The source code to set
        """
        self._source = value

    @property
    def html(self) -> str | None:
        """
        Get the revision's HTML display

        Automatically fetches the HTML display if not yet acquired.

        Returns
        -------
        str | None
            The revision's HTML display
        """
        if not self.is_html_acquired():
            PageRevisionCollection(self.page, [self]).get_htmls()
        return self._html

    @html.setter
    def html(self, value: str) -> None:
        """
        Set the revision's HTML display

        Parameters
        ----------
        value : str
            The HTML display to set
        """
        self._html = value
