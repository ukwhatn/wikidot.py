"""
Module for handling Wikidot page file attachments

This module provides classes and functions related to files attached
to Wikidot site pages. It enables operations such as retrieving file information.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from ..connector.ajax import require_body
from ..util.amc_body import flag, omit_falsy

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

        html = BeautifulSoup(require_body(response, "files/PageFilesModule"), "lxml")
        files = PageFileCollection._parse_from_html(page, html)

        return PageFileCollection(page=page, files=files)

    @staticmethod
    def check_exists(page: "Page", filename: str) -> bool:
        """
        Check whether a file with the given name exists on the page (FileAction/checkFileExists)

        Parameters
        ----------
        page : Page
            Page to check
        filename : str
            File name to check for

        Returns
        -------
        bool
            Whether the file exists
        """
        response = page.site.amc_request(
            [
                {
                    "action": "FileAction",
                    "event": "checkFileExists",
                    "moduleName": "Empty",
                    "filename": filename,
                    "pageId": page.id,
                }
            ]
        )[0]
        return bool(response.json().get("exists"))

    @staticmethod
    def get_upload_form(page: "Page") -> str:
        """
        Get the rendered file upload form for a page (files/FileUploadModule)

        Returns the HTML form only; the actual upload goes through the
        separate multipart endpoint (see page_file_upload.py / D8 Task 3-5b),
        not this module.

        Parameters
        ----------
        page : Page
            Page to render the upload form for

        Returns
        -------
        str
            Rendered HTML body
        """
        response = page.site.amc_request([{"moduleName": "files/FileUploadModule", "pageId": page.id}])[0]
        return require_body(response, "files/FileUploadModule")

    @staticmethod
    def get_manager(page: "Page") -> str:
        """
        Get the rendered site-wide file manager view (files/manager/FileManagerModule)

        The exact parameter set for a manager view scoped beyond a single
        page was not captured during wire-format research (only that this
        module exists, per 32_tasks.md Task 3-5); this sends `pageId` as
        the one documented per-page parameter shape and returns the raw
        body, which callers can parse or otherwise use as-is.

        Parameters
        ----------
        page : Page
            Page to scope the file manager view to

        Returns
        -------
        str
            Rendered HTML body
        """
        response = page.site.amc_request([{"moduleName": "files/manager/FileManagerModule", "pageId": page.id}])[0]
        return require_body(response, "files/manager/FileManagerModule")

    @staticmethod
    def upload(
        page: "Page",
        filename: str,
        content: bytes,
        *,
        multikey: str | None = None,
    ) -> dict[str, str]:
        """
        Upload a file to a page (multipart, /default--flow/files__UploadTarget)

        UNVERIFIED AGAINST A LIVE WIKIDOT INSTANCE -- see
        AjaxModuleConnectorClient.upload_file's docstring for what is and
        isn't confirmed. Does not go through site.amc_request(): this
        endpoint returns an HTML fragment rather than the AMC JSON
        envelope, so it uses a dedicated client method instead.

        Parameters
        ----------
        page : Page
            Page to attach the file to
        filename : str
            File name as it will appear on the page
        content : bytes
            File content
        multikey : str | None, default None
            Multi-file upload session key, required when uploading more
            than one file so Wikidot can group them for
            multi_upload_complete()

        Returns
        -------
        dict[str, str]
            Parsed response fields among "status" / "message" / "filename"
        """
        page.site.client.login_check()
        return page.site.client.amc_client.upload_file(
            page_id=page.id,
            filename=filename,
            content=content,
            site_name=page.site.unix_name,
            site_ssl_supported=page.site.ssl_supported,
            multikey=multikey,
        )

    @staticmethod
    def multi_upload_complete(page: "Page", multikey: str, filenames: list[str]) -> None:
        """
        Notify Wikidot that a batch of multipart uploads has finished (FileAction/multiUploadComplete)

        Parameters
        ----------
        page : Page
            Page the files were uploaded to
        multikey : str
            Multi-file upload session key shared by the uploads in this batch
        filenames : list[str]
            File names uploaded in this batch

        Raises
        ------
        LoginRequiredException
            When not logged in
        """
        page.site.client.login_check()
        page.site.amc_request(
            [
                {
                    "action": "FileAction",
                    "event": "multiUploadComplete",
                    "moduleName": "Empty",
                    "multikey": multikey,
                    "fnames": json.dumps(filenames),
                    "page_id": page.id,
                }
            ]
        )


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

    def get_rename_form(self) -> str:
        """
        Get the rendered rename form for this file (files/FileRenameWinModule)

        Returns
        -------
        str
            Rendered HTML body
        """
        response = self.page.site.amc_request([{"moduleName": "files/FileRenameWinModule", "file_id": self.id}])[0]
        return require_body(response, "files/FileRenameWinModule")

    def get_move_form(self) -> str:
        """
        Get the rendered move form for this file (files/FileMoveWinModule)

        Returns
        -------
        str
            Rendered HTML body
        """
        response = self.page.site.amc_request([{"moduleName": "files/FileMoveWinModule", "file_id": self.id}])[0]
        return require_body(response, "files/FileMoveWinModule")

    def get_info(self) -> str:
        """
        Get the rendered detail view for this file (files/FileInformationWinModule)

        Returns
        -------
        str
            Rendered HTML body
        """
        response = self.page.site.amc_request([{"moduleName": "files/FileInformationWinModule", "file_id": self.id}])[0]
        return require_body(response, "files/FileInformationWinModule")

    def rename(self, new_name: str, force: bool = False) -> "PageFile":
        """
        Rename this file (FileAction/renameFile)

        Parameters
        ----------
        new_name : str
            New file name
        force : bool, default False
            Whether to overwrite if a file with the new name already exists

        Returns
        -------
        PageFile
            Self (for method chaining)

        Raises
        ------
        LoginRequiredException
            When not logged in
        WikidotStatusCodeException
            When the rename fails. `status_code` is "file_exists" (a file
            with that name already exists; response carries `body`) or
            "name_error" (invalid name; response carries `message`)
        """
        self.page.site.client.login_check()
        self.page.site.amc_request(
            [
                {
                    "action": "FileAction",
                    "event": "renameFile",
                    "moduleName": "Empty",
                    "file_id": self.id,
                    "new_name": new_name,
                    **omit_falsy(force=flag(force)),
                }
            ]
        )
        self.name = new_name
        return self

    def move(self, destination_page_name: str, force: bool = False) -> None:
        """
        Move this file to another page (FileAction/moveFile)

        Parameters
        ----------
        destination_page_name : str
            Fullname of the destination page
        force : bool, default False
            Whether to overwrite if a file with the same name already
            exists on the destination page

        Raises
        ------
        LoginRequiredException
            When not logged in
        WikidotStatusCodeException
            When the move fails. `status_code` is "file_exists" /
            "no_destination" / "no_destination_permission"

        Notes
        -----
        After a successful move this object's `page` reference still
        points at the source page; re-fetch the file from the
        destination page if you need an up-to-date PageFile
        """
        self.page.site.client.login_check()
        self.page.site.amc_request(
            [
                {
                    "action": "FileAction",
                    "event": "moveFile",
                    "moduleName": "Empty",
                    "file_id": self.id,
                    "destination_page_name": destination_page_name,
                    **omit_falsy(force=flag(force)),
                }
            ]
        )

    def delete(self, confirm: bool = False) -> None:
        """
        Delete this file (FileAction/deleteFile)

        Parameters
        ----------
        confirm : bool, default False
            Must be explicitly set to True. This is a destructive,
            irreversible operation

        Raises
        ------
        ValueError
            When confirm is not True
        LoginRequiredException
            When not logged in
        """
        if not confirm:
            raise ValueError("delete() is destructive; pass confirm=True to proceed")
        self.page.site.client.login_check()
        self.page.site.amc_request(
            [
                {
                    "action": "FileAction",
                    "event": "deleteFile",
                    "moduleName": "Empty",
                    "file_id": self.id,
                }
            ]
        )
