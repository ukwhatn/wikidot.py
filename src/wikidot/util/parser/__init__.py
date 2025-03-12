"""
Wikidotサイトの各種要素をパースするためのユーティリティモジュール

このパッケージには、Wikidotサイトから取得したHTMLや特定の形式の要素を
パースするためのユーティリティ関数が含まれている。
"""

from .odate import odate_parse as odate
from .user import user_parse as user

__all__ = ["odate", "user"]
