"""Userモジュールのユニットテスト"""

from unittest.mock import MagicMock

import pytest
from pytest_httpx import HTTPXMock

from wikidot.common.exceptions import NoElementException, NotFoundException
from wikidot.module.user import (
    AnonymousUser,
    DeletedUser,
    GuestUser,
    User,
    UserCollection,
    WikidotUser,
)


class TestUserDataclasses:
    """ユーザーデータクラスのテスト"""

    def test_user_str(self, mock_client_no_http: MagicMock) -> None:
        """User.__str__が正しい文字列を返す"""
        user = User(
            client=mock_client_no_http,
            id=12345,
            name="test-user",
            unix_name="test-user",
            avatar_url="http://example.com/avatar.png",
        )

        result = str(user)

        assert "User(" in result
        assert "id=12345" in result
        assert "name=test-user" in result

    def test_deleted_user_defaults(self, mock_client_no_http: MagicMock) -> None:
        """DeletedUserのデフォルト値が正しい"""
        user = DeletedUser(client=mock_client_no_http, id=99999)

        assert user.name == "account deleted"
        assert user.unix_name == "account_deleted"
        assert user.avatar_url is None

    def test_anonymous_user_defaults(self, mock_client_no_http: MagicMock) -> None:
        """AnonymousUserのデフォルト値が正しい"""
        user = AnonymousUser(client=mock_client_no_http, ip="192.168.1.1")

        assert user.name == "Anonymous"
        assert user.unix_name == "anonymous"
        assert user.id is None
        assert user.avatar_url is None

    def test_guest_user_defaults(self, mock_client_no_http: MagicMock) -> None:
        """GuestUserのデフォルト値が正しい"""
        user = GuestUser(
            client=mock_client_no_http,
            name="Guest Name",
            avatar_url="http://gravatar.com/avatar/abc",
        )

        assert user.id is None
        assert user.unix_name is None
        assert user.ip is None

    def test_wikidot_user_defaults(self, mock_client_no_http: MagicMock) -> None:
        """WikidotUserのデフォルト値が正しい"""
        user = WikidotUser(client=mock_client_no_http)

        assert user.name == "Wikidot"
        assert user.unix_name == "wikidot"
        assert user.id is None
        assert user.avatar_url is None


class TestUserFromName:
    """User.from_name のテスト"""

    def test_from_name_success(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock, user_profile_html: str
    ) -> None:
        """ユーザー名からユーザーを取得できる"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/user:info/test-user",
            text=user_profile_html,
        )

        result = User.from_name(mock_client_no_http, "test-user")

        assert result is not None
        assert isinstance(result, User)
        assert result.id == 12345
        assert result.name == "test-user"

    def test_from_name_not_found_no_raise(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock, user_profile_not_found_html: str
    ) -> None:
        """ユーザーが見つからない場合Noneを返す"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/user:info/nonexistent",
            text=user_profile_not_found_html,
        )

        result = User.from_name(mock_client_no_http, "nonexistent", raise_when_not_found=False)

        assert result is None

    def test_from_name_not_found_raise(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock, user_profile_not_found_html: str
    ) -> None:
        """ユーザーが見つからない場合NotFoundException"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/user:info/nonexistent",
            text=user_profile_not_found_html,
        )

        with pytest.raises(NotFoundException):
            User.from_name(mock_client_no_http, "nonexistent", raise_when_not_found=True)


class TestUserCollection:
    """UserCollection のテスト"""

    def test_from_names_multiple(self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock) -> None:
        """複数ユーザーを一度に取得できる"""
        html1 = """
        <!DOCTYPE html>
        <html>
        <head><title>user1 - Wikidot</title></head>
        <body>
        <div id="user-info">
            <h1 class="profile-title">user1</h1>
            <a class="btn btn-default btn-xs" href="http://www.wikidot.com/userkarma.php/111">
                Karma
            </a>
        </div>
        </body>
        </html>
        """
        html2 = """
        <!DOCTYPE html>
        <html>
        <head><title>user2 - Wikidot</title></head>
        <body>
        <div id="user-info">
            <h1 class="profile-title">user2</h1>
            <a class="btn btn-default btn-xs" href="http://www.wikidot.com/userkarma.php/222">
                Karma
            </a>
        </div>
        </body>
        </html>
        """
        httpx_mock.add_response(
            url="https://www.wikidot.com/user:info/user1",
            text=html1,
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/user:info/user2",
            text=html2,
        )

        result = UserCollection.from_names(mock_client_no_http, ["user1", "user2"])

        assert len(result) == 2
        names = [u.name for u in result]
        assert "user1" in names
        assert "user2" in names

    def test_from_names_skip_not_found(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock, user_profile_not_found_html: str
    ) -> None:
        """見つからないユーザーをスキップできる"""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>exists - Wikidot</title></head>
        <body>
        <div id="user-info">
            <h1 class="profile-title">exists</h1>
            <a class="btn btn-default btn-xs" href="http://www.wikidot.com/account/messages#/new/333">
                PM
            </a>
        </div>
        </body>
        </html>
        """
        httpx_mock.add_response(
            url="https://www.wikidot.com/user:info/exists",
            text=html,
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/user:info/nonexistent",
            text=user_profile_not_found_html,
        )

        result = UserCollection.from_names(mock_client_no_http, ["exists", "nonexistent"], raise_when_not_found=False)

        assert len(result) == 1
        assert result[0].name == "exists"

    def test_from_names_missing_id_element(self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock) -> None:
        """ID要素がない場合NoElementException"""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>bad - Wikidot</title></head>
        <body>
        <div id="user-info">
            <h1 class="profile-title">bad</h1>
            <!-- ID要素がない -->
        </div>
        </body>
        </html>
        """
        httpx_mock.add_response(
            url="https://www.wikidot.com/user:info/bad",
            text=html,
        )

        with pytest.raises(NoElementException) as exc_info:
            UserCollection.from_names(mock_client_no_http, ["bad"])

        assert "ID" in str(exc_info.value)

    def test_from_names_missing_name_element(self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock) -> None:
        """名前要素がない場合NoElementException"""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>bad - Wikidot</title></head>
        <body>
        <div id="user-info">
            <!-- 名前要素がない -->
            <a class="btn btn-default btn-xs" href="http://www.wikidot.com/account/messages#/new/123">
                PM
            </a>
        </div>
        </body>
        </html>
        """
        httpx_mock.add_response(
            url="https://www.wikidot.com/user:info/bad",
            text=html,
        )

        with pytest.raises(NoElementException) as exc_info:
            UserCollection.from_names(mock_client_no_http, ["bad"])

        assert "name" in str(exc_info.value)

    def test_iteration(self, mock_client_no_http: MagicMock) -> None:
        """UserCollectionはイテレート可能"""
        users = UserCollection(
            [
                User(client=mock_client_no_http, id=1, name="a", unix_name="a"),
                User(client=mock_client_no_http, id=2, name="b", unix_name="b"),
            ]
        )

        names = [u.name for u in users]

        assert names == ["a", "b"]
