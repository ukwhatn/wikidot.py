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
        users = QuickModule._request("MemberLookupQModule", site_id, query)["users"]
        if users is False:
            return []
        return [QMCUser(id=int(user["user_id"]), name=user["name"]) for user in users]

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
        users = QuickModule._request("UserLookupQModule", site_id, query)["users"]
        return [QMCUser(id=int(user["user_id"]), name=user["name"]) for user in users]

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
        pages = QuickModule._request("PageLookupQModule", site_id, query)["pages"]
        return [QMCPage(title=page["title"], unix_name=page["unix_name"]) for page in pages]
