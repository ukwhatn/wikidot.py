from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from wikidot.module.page_source import PageSource

if TYPE_CHECKING:
    from wikidot.module.page import Page
    from wikidot.module.user import AbstractUser


class PageRevisionCollection(list["PageRevision"]):
    def __init__(self, page: "Page" = None, revisions: list["PageRevision"] = None):
        super().__init__(revisions or [])
        self.page = page or revisions[0].page

    def __iter__(self) -> Iterator["PageRevision"]:
        return super().__iter__()

    @staticmethod
    def _acquire_sources(page, revisions: list["PageRevision"]):
        target_revisions = [
            revision for revision in revisions if not revision.is_source_acquired()
        ]

        if len(target_revisions) == 0:
            return revisions

        responses = page.site.amc_request(
            [
                {"moduleName": "history/PageSourceModule", "revision_id": revision.id}
                for revision in target_revisions
            ]
        )

        for revision, response in zip(target_revisions, responses):
            body = response.json()["body"]
            body_html = BeautifulSoup(body, "lxml")
            revision.source = PageSource(
                page=page,
                wiki_text=body_html.select_one("div.page-source").text.strip(),
            )

        return revisions

    def get_sources(self):
        return self._acquire_sources(self.page, self)

    @staticmethod
    def _acquire_htmls(page, revisions: list["PageRevision"]):
        target_revisions = [
            revision for revision in revisions if not revision.is_html_acquired()
        ]

        if len(target_revisions) == 0:
            return revisions

        responses = page.site.amc_request(
            [
                {"moduleName": "history/PageVersionModule", "revision_id": revision.id}
                for revision in target_revisions
            ]
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
        return self._acquire_htmls(self.page, self)


@dataclass
class PageRevision:
    page: "Page"
    id: int
    rev_no: int
    created_by: "AbstractUser"
    created_at: datetime
    comment: str
    _source: Optional["PageSource"] = None
    _html: Optional[str] = None

    def is_source_acquired(self) -> bool:
        return self._source is not None

    def is_html_acquired(self) -> bool:
        return self._html is not None

    @property
    def source(self) -> "PageSource":
        if not self.is_source_acquired():
            PageRevisionCollection(self.page, [self]).get_sources()
        return self._source

    @source.setter
    def source(self, value: "PageSource"):
        self._source = value

    @property
    def html(self) -> str:
        if not self.is_html_acquired():
            PageRevisionCollection(self.page, [self]).get_htmls()
        return self._html

    @html.setter
    def html(self, value: str):
        self._html = value
