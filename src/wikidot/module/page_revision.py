"""
Wikidotページの編集履歴（リビジョン）を扱うモジュール

このモジュールは、Wikidotページの編集履歴（リビジョン）に関連するクラスや機能を提供する。
リビジョンの取得、ソースの取得、HTML表示などの操作が可能。
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from ..common.exceptions import NoElementException
from .page_source import PageSource

if TYPE_CHECKING:
    from .page import Page
    from .user import AbstractUser


class PageRevisionCollection(list["PageRevision"]):
    """
    ページリビジョンのコレクションを表すクラス

    ページの編集履歴（リビジョン）の複数バージョンを格納し、一括して操作するための
    リスト拡張クラス。ソースコードやHTMLの一括取得など、便利な機能を提供する。
    """

    def __init__(
        self,
        page: Optional["Page"] = None,
        revisions: Optional[list["PageRevision"]] = None,
    ):
        """
        初期化メソッド

        Parameters
        ----------
        page : Page | None, default None
            リビジョンが属するページ。Noneの場合は最初のリビジョンから推測する
        revisions : list[PageRevision] | None, default None
            格納するリビジョンのリスト
        """
        super().__init__(revisions or [])
        self.page = page or self[0].page if len(self) > 0 else None

    def __iter__(self) -> Iterator["PageRevision"]:
        """
        コレクション内のリビジョンを順に返すイテレータ

        Returns
        -------
        Iterator[PageRevision]
            リビジョンオブジェクトのイテレータ
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["PageRevision"]:
        """
        指定したリビジョンIDのリビジョンを取得する

        Parameters
        ----------
        id : int
            取得するリビジョンのID

        Returns
        -------
        PageRevision | None
            指定したIDのリビジョン。見つからない場合はNone
        """
        for revision in self:
            if revision.id == id:
                return revision
        return None

    @staticmethod
    def _acquire_sources(page, revisions: list["PageRevision"]):
        """
        複数のリビジョンのソースコードを一括取得する内部メソッド

        未取得のリビジョンソースコードを一括でリクエストし、取得する。

        Parameters
        ----------
        page : Page
            リビジョンが属するページ
        revisions : list[PageRevision]
            ソースコードを取得するリビジョンのリスト

        Returns
        -------
        list[PageRevision]
            ソースコード情報が更新されたリビジョンのリスト

        Raises
        ------
        NoElementException
            ソース要素が見つからない場合
        """
        target_revisions = [revision for revision in revisions if not revision.is_source_acquired()]

        if len(target_revisions) == 0:
            return revisions

        responses = page.site.amc_request(
            [{"moduleName": "history/PageSourceModule", "revision_id": revision.id} for revision in target_revisions]
        )

        for revision, response in zip(target_revisions, responses):
            body = response.json()["body"]
            body_html = BeautifulSoup(body, "lxml")
            wiki_text_elem = body_html.select_one("div.page-source")
            if wiki_text_elem is None:
                raise NoElementException("Wiki text element not found")
            revision.source = PageSource(
                page=page,
                wiki_text=wiki_text_elem.text.strip(),
            )

        return revisions

    def get_sources(self):
        """
        コレクション内のすべてのリビジョンのソースコードを取得する

        Returns
        -------
        PageRevisionCollection
            自身（メソッドチェーン用）
        """
        return self._acquire_sources(self.page, self)

    @staticmethod
    def _acquire_htmls(page, revisions: list["PageRevision"]):
        """
        複数のリビジョンのHTML表示を一括取得する内部メソッド

        未取得のリビジョンHTMLを一括でリクエストし、取得する。

        Parameters
        ----------
        page : Page
            リビジョンが属するページ
        revisions : list[PageRevision]
            HTMLを取得するリビジョンのリスト

        Returns
        -------
        list[PageRevision]
            HTML情報が更新されたリビジョンのリスト
        """
        target_revisions = [revision for revision in revisions if not revision.is_html_acquired()]

        if len(target_revisions) == 0:
            return revisions

        responses = page.site.amc_request(
            [{"moduleName": "history/PageVersionModule", "revision_id": revision.id} for revision in target_revisions]
        )

        for revision, response in zip(target_revisions, responses):
            body = response.json()["body"]
            # onclick="document.getElementById('page-version-info').style.display='none'">(.*?)</a>\n\t</div>\n\n\n\n
            # 以降をソースとして取得
            source = body.split(
                "onclick=\"document.getElementById('page-version-info').style.display='none'\">",
                maxsplit=1,
            )[1]
            source = source.split("</a>\n\t</div>\n\n\n\n", maxsplit=1)[1]
            revision._html = source

        return revisions

    def get_htmls(self):
        """
        コレクション内のすべてのリビジョンのHTML表示を取得する

        Returns
        -------
        PageRevisionCollection
            自身（メソッドチェーン用）
        """
        return self._acquire_htmls(self.page, self)


@dataclass
class PageRevision:
    """
    ページのリビジョン（編集履歴のバージョン）を表すクラス

    ページの特定のバージョンに関する情報を保持する。リビジョン番号、作成者、作成日時、
    編集コメントなどの基本情報に加え、ソースコードやHTML表示へのアクセス機能を提供する。

    Attributes
    ----------
    page : Page
        リビジョンが属するページ
    id : int
        リビジョンID
    rev_no : int
        リビジョン番号
    created_by : AbstractUser
        リビジョンの作成者
    created_at : datetime
        リビジョンの作成日時
    comment : str
        編集コメント
    _source : PageSource | None, default None
        リビジョンのソースコード（内部キャッシュ用）
    _html : str | None, default None
        リビジョンのHTML表示（内部キャッシュ用）
    """

    page: "Page"
    id: int
    rev_no: int
    created_by: "AbstractUser"
    created_at: datetime
    comment: str
    _source: Optional["PageSource"] = None
    _html: Optional[str] = None

    def is_source_acquired(self) -> bool:
        """
        ソースコードが既に取得済みかどうかを確認する

        Returns
        -------
        bool
            ソースコードが取得済みの場合はTrue、そうでない場合はFalse
        """
        return self._source is not None

    def is_html_acquired(self) -> bool:
        """
        HTML表示が既に取得済みかどうかを確認する

        Returns
        -------
        bool
            HTML表示が取得済みの場合はTrue、そうでない場合はFalse
        """
        return self._html is not None

    @property
    def source(self) -> Optional["PageSource"]:
        """
        リビジョンのソースコードを取得する

        ソースコードが未取得の場合は自動的に取得処理を行う。

        Returns
        -------
        PageSource | None
            リビジョンのソースコード
        """
        if not self.is_source_acquired():
            PageRevisionCollection(self.page, [self]).get_sources()
        return self._source

    @source.setter
    def source(self, value: "PageSource"):
        """
        リビジョンのソースコードを設定する

        Parameters
        ----------
        value : PageSource
            設定するソースコード
        """
        self._source = value

    @property
    def html(self) -> Optional[str]:
        """
        リビジョンのHTML表示を取得する

        HTML表示が未取得の場合は自動的に取得処理を行う。

        Returns
        -------
        str | None
            リビジョンのHTML表示
        """
        if not self.is_html_acquired():
            PageRevisionCollection(self.page, [self]).get_htmls()
        return self._html

    @html.setter
    def html(self, value: str):
        """
        リビジョンのHTML表示を設定する

        Parameters
        ----------
        value : str
            設定するHTML表示
        """
        self._html = value
