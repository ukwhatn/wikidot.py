"""
Wikidotページのファイル添付を扱うモジュール

このモジュールは、Wikidotサイトのページに添付されたファイルに関連する
クラスや機能を提供する。ファイルの情報取得などの操作が可能。
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from .page import Page


class PageFileCollection(list["PageFile"]):
    """
    ページファイルのコレクションを表すクラス

    ページに添付された複数のファイルを格納し、一括して操作するためのリスト拡張クラス。
    """

    def __init__(
        self,
        page: Optional["Page"] = None,
        files: Optional[list["PageFile"]] = None,
    ):
        """
        初期化メソッド

        Parameters
        ----------
        page : Page | None, default None
            ファイルが属するページ。Noneの場合は最初のファイルから推測する
        files : list[PageFile] | None, default None
            格納するファイルのリスト
        """
        super().__init__(files or [])

        if page is not None:
            self.page = page
        elif len(self) > 0:
            self.page = self[0].page

    def __iter__(self) -> Iterator["PageFile"]:
        """
        コレクション内のファイルを順に返すイテレータ

        Returns
        -------
        Iterator[PageFile]
            ファイルオブジェクトのイテレータ
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["PageFile"]:
        """
        指定したIDのファイルを取得する

        Parameters
        ----------
        id : int
            取得するファイルのID

        Returns
        -------
        PageFile | None
            指定したIDのファイル。存在しない場合はNone
        """
        for file in self:
            if file.id == id:
                return file
        return None

    def find_by_name(self, name: str) -> Optional["PageFile"]:
        """
        指定した名前のファイルを取得する

        Parameters
        ----------
        name : str
            取得するファイルの名前

        Returns
        -------
        PageFile | None
            指定した名前のファイル。存在しない場合はNone
        """
        for file in self:
            if file.name == name:
                return file
        return None

    @staticmethod
    def _parse_size(size_text: str) -> int:
        """
        ファイルサイズ文字列をバイト数に変換する

        Parameters
        ----------
        size_text : str
            サイズ文字列（例: "1.5 kB", "2 MB", "500 Bytes"）

        Returns
        -------
        int
            バイト数
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
    def acquire(page: "Page") -> "PageFileCollection":
        """
        ページに添付されたファイル一覧を取得する

        Parameters
        ----------
        page : Page
            ファイルを取得するページ

        Returns
        -------
        PageFileCollection
            ページに添付されたファイルのコレクション
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
        files_table = html.select_one("table.page-files")

        if files_table is None:
            return PageFileCollection(page=page, files=[])

        files: list["PageFile"] = []
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
            mime_type = mime_elem.get("title", "") if mime_elem else ""

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

        return PageFileCollection(page=page, files=files)


@dataclass
class PageFile:
    """
    Wikidotページの添付ファイルを表すクラス

    ページに添付された個別のファイルに関する情報を保持する。

    Attributes
    ----------
    page : Page
        ファイルが添付されているページ
    id : int
        ファイルID
    name : str
        ファイル名
    url : str
        ファイルのダウンロードURL
    mime_type : str
        ファイルのMIMEタイプ
    size : int
        ファイルサイズ（バイト）
    """

    page: "Page"
    id: int
    name: str
    url: str
    mime_type: str
    size: int

    def __str__(self):
        """
        オブジェクトの文字列表現

        Returns
        -------
        str
            ファイルの文字列表現
        """
        return f"PageFile(id={self.id}, name={self.name}, url={self.url}, mime_type={self.mime_type}, size={self.size})"
