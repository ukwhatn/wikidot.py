"""
Wikidotページのソースコードを扱うモジュール

このモジュールは、Wikidotページのソースコード（Wikidot記法）に関連するクラスや機能を提供する。
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .page import Page


@dataclass
class PageSource:
    """
    ページのソースコード（Wikidot記法）を表すクラス

    Wikidotページのソースコード（Wikidot記法）を保持し、基本的な操作を提供する。
    ページの現在または特定リビジョンのソースコードを表現する。

    Attributes
    ----------
    page : Page
        ソースコードが属するページ
    wiki_text : str
        ページのソースコード（Wikidot記法）
    """

    page: "Page"
    wiki_text: str
