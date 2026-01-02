"""
Module for handling Wikidot page file attachments

This module provides classes and functions related to files attached
to Wikidot site pages. It enables operations such as retrieving file information.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from .page import Page


class PageFileCollection(list["PageFile"]):
    """
    Class representing a collection of page files

    A list extension class for storing and operating on multiple files
    attached to a page in bulk.
    """

    page: "Page"

    def __init__(
        self,
        page: Optional["Page"] = None,
        files: list["PageFile"] | None = None,
    ):
        """
        Initialize the collection

        Parameters
        ----------
        page : Page | None, default None
            The page the files belong to. If None, inferred from the first file
        files : list[PageFile] | None, default None
            List of files to store
        """
        super().__init__(files or [])

        if page is not None:
            self.page = page
        elif len(self) > 0:
            self.page = self[0].page

    def __iter__(self) -> Iterator["PageFile"]:
        """
        Return an iterator over the files in the collection

        Returns
        -------
        Iterator[PageFile]
            Iterator of file objects
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["PageFile"]:
        """
        Get the file with the specified ID

        Parameters
        ----------
        id : int
            The ID of the file to retrieve

        Returns
        -------
        PageFile | None
            The file with the specified ID, or None if not found
        """
        for file in self:
            if file.id == id:
                return file
        return None

    def find_by_name(self, name: str) -> Optional["PageFile"]:
        """
        Get the file with the specified name

        Parameters
        ----------
        name : str
            The name of the file to retrieve

        Returns
        -------
        PageFile | None
            The file with the specified name, or None if not found
        """
        for file in self:
            if file.name == name:
                return file
        return None

    @staticmethod
    def _parse_size(size_text: str) -> int:
        """
        Convert file size string to bytes

        Parameters
        ----------
        size_text : str
            Size string (e.g., "1.5 kB", "2 MB", "500 Bytes")

        Returns
        -------
        int
            Size in bytes
        """
        size_text = size_text.strip()
        if "Bytes" in size_text:
            return int(float(size_text.replace("Bytes", "").strip()))
        elif "kB" in size_text:
            return int(float(size_text.replace("kB", "").strip()) * 1000)
        elif "MB" in size_text:
            return int(float(size_text.replace("MB", "").strip()) * 1000000)
        elif "GB" in size_text:
            return int(float(size_text.replace("GB", "").strip()) * 1000000000)
        return 0

    @staticmethod
    def _parse_from_html(page: "Page", html: BeautifulSoup) -> list["PageFile"]:
        """
        Parse file information from HTML response

        Internal helper method used by acquire() and PageCollection._acquire_page_files().

        Parameters
        ----------
        page : Page
            The page the files belong to
        html : BeautifulSoup
            Parsed HTML response from files/PageFilesModule

        Returns
        -------
        list[PageFile]
            List of parsed PageFile objects
        """
        files_table = html.select_one("table.page-files")

        if files_table is None:
            return []

        files: list[PageFile] = []
        for row in files_table.select("tbody tr[id^='file-row-']"):
            row_id = row.get("id")
            if row_id is None:
                continue

            file_id = int(str(row_id).removeprefix("file-row-"))
            tds = row.select("td")
            if len(tds) < 3:
                continue

            link_elem = tds[0].select_one("a")
            if link_elem is None:
                continue

            name = link_elem.get_text().strip()
            href = link_elem.get("href", "")
            url = f"{page.site.url}{href}"

            mime_elem = tds[1].select_one("span")
            mime_type = str(mime_elem.get("title", "")) if mime_elem else ""

            size_text = tds[2].get_text().strip()
            size = PageFileCollection._parse_size(size_text)

            files.append(
                PageFile(
                    page=page,
                    id=file_id,
                    name=name,
                    url=url,
                    mime_type=mime_type,
                    size=size,
                )
            )

        return files

    @staticmethod
    def acquire(page: "Page") -> "PageFileCollection":
        """
        Get the list of files attached to a page

        Parameters
        ----------
        page : Page
            The page to retrieve files from

        Returns
        -------
        PageFileCollection
            Collection of files attached to the page
        """
        response = page.site.amc_request(
            [
                {
                    "moduleName": "files/PageFilesModule",
                    "page_id": page.id,
                }
            ]
        )[0]

        html = BeautifulSoup(response.json()["body"], "lxml")
        files = PageFileCollection._parse_from_html(page, html)

        return PageFileCollection(page=page, files=files)


@dataclass
class PageFile:
    """
    Class representing a Wikidot page attachment file

    Holds information about an individual file attached to a page.

    Attributes
    ----------
    page : Page
        The page the file is attached to
    id : int
        File ID
    name : str
        File name
    url : str
        File download URL
    mime_type : str
        File MIME type
    size : int
        File size in bytes
    """

    page: "Page"
    id: int
    name: str
    url: str
    mime_type: str
    size: int

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the file
        """
        return f"PageFile(id={self.id}, name={self.name}, url={self.url}, mime_type={self.mime_type}, size={self.size})"
