from dataclasses import dataclass

import httpx


@dataclass
class QMCUser:
    """QuickModuleから返されるユーザー情報を格納するクラス

    Attributes
    ----------
    id: int
        ユーザーID
    name: str
        ユーザー名
    """

    id: int
    name: str


@dataclass
class QMCPage:
    """QuickModuleから返されるページ情報を格納するクラス

    Attributes
    ----------
    title: str
        ページタイトル
    unix_name: str
        ページのUNIX名
    """

    title: str
    unix_name: str


class QuickModule:
    @staticmethod
    def _request(
        module_name: str,
        site_id: int,
        query: str,
    ):
        """リクエストを送信する

        Parameters
        ----------
        module_name: str
            モジュール名
        site_id: int
            サイトID
        query: str
            クエリ
        """

        if module_name not in [
            "MemberLookupQModule",
            "UserLookupQModule",
            "PageLookupQModule",
        ]:
            raise ValueError("Invalid module name")

        url = f"https://www.wikidot.com/quickmodule.php?module={module_name}&s={site_id}&q={query}"
        response = httpx.get(url, timeout=300)
        if response.status_code == httpx.codes.INTERNAL_SERVER_ERROR:
            raise ValueError("Site is not found")
        return response.json()

    @staticmethod
    def _generic_lookup(module_name: str, site_id: int, query: str, response_key: str, 
                       item_class, item_mapping):
        """汎用的な検索メソッド

        Parameters
        ----------
        module_name: str
            モジュール名
        site_id: int
            サイトID
        query: str
            クエリ
        response_key: str
            レスポンスから取得するキー
        item_class: type
            返すアイテムのクラス
        item_mapping: callable
            レスポンスアイテムからクラスインスタンスへの変換関数

        Returns
        -------
        list
            アイテムのリスト
        """
        items = QuickModule._request(module_name, site_id, query)[response_key]
        # member_lookupの特殊ケースを処理
        if items is False:
            return []
        return [item_mapping(item_class, item) for item in items]

    @staticmethod
    def member_lookup(site_id: int, query: str):
        """メンバーを検索する

        Parameters
        ----------
        site_id: int
            サイトID
        query: str
            クエリ

        Returns
        -------
        list[QMCUser]
            ユーザーのリスト
        """
        return QuickModule._generic_lookup(
            "MemberLookupQModule", 
            site_id, 
            query, 
            "users",
            QMCUser,
            lambda cls, item: cls(id=int(item["user_id"]), name=item["name"])
        )

    @staticmethod
    def user_lookup(site_id: int, query: str):
        """ユーザーを検索する

        Parameters
        ----------
        site_id: int
            サイトID
        query: str
            クエリ

        Returns
        -------
        list[QMCUser]
            ユーザーのリスト
        """
        return QuickModule._generic_lookup(
            "UserLookupQModule",
            site_id,
            query,
            "users",
            QMCUser,
            lambda cls, item: cls(id=int(item["user_id"]), name=item["name"])
        )

    @staticmethod
    def page_lookup(site_id: int, query: str):
        """ページを検索する

        Parameters
        ----------
        site_id: int
            サイトID
        query: str
            クエリ

        Returns
        -------
        list[QMCPage]
            ページのリスト
        """
        return QuickModule._generic_lookup(
            "PageLookupQModule",
            site_id,
            query,
            "pages",
            QMCPage,
            lambda cls, item: cls(title=item["title"], unix_name=item["unix_name"])
        )
