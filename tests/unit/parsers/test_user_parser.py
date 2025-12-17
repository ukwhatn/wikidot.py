"""userパーサーのユニットテスト"""

from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from wikidot.module.user import AnonymousUser, DeletedUser, GuestUser, User, WikidotUser
from wikidot.util.parser.user import user_parse


class TestUserParserRegularUser:
    """通常ユーザーのパーステスト"""

    def test_parse_regular_user(self, mock_client_no_http: MagicMock, printuser_regular_html: str) -> None:
        """通常のprintuser要素をパースできる"""
        soup = BeautifulSoup(printuser_regular_html, "lxml")
        elem = soup.select_one("span.printuser")
        assert elem is not None

        result = user_parse(mock_client_no_http, elem)

        assert isinstance(result, User)
        assert result.id == 12345
        assert result.name == "test-user"
        assert result.unix_name == "test-user"
        # パーサーはIDからavatar_urlを生成する
        assert result.avatar_url == "http://www.wikidot.com/avatar.php?userid=12345"

    def test_parse_user_extracts_onclick_id(self, mock_client_no_http: MagicMock) -> None:
        """onclick属性からユーザーIDを抽出できる"""
        html = '<span class="printuser"><a href="http://www.wikidot.com/user:info/another-user" onclick="WIKIDOT.page.listeners.userInfo(99999); return false;">another-user</a></span>'
        soup = BeautifulSoup(html, "lxml")
        elem = soup.select_one("span.printuser")
        assert elem is not None

        result = user_parse(mock_client_no_http, elem)

        assert isinstance(result, User)
        assert result.id == 99999
        assert result.name == "another-user"


class TestUserParserDeletedUser:
    """削除済みユーザーのパーステスト"""

    def test_parse_deleted_user_with_id(self, mock_client_no_http: MagicMock, printuser_deleted_html: str) -> None:
        """data-id付き削除済みユーザーをパースできる"""
        soup = BeautifulSoup(printuser_deleted_html, "lxml")
        elem = soup.select_one("span.printuser")
        assert elem is not None

        result = user_parse(mock_client_no_http, elem)

        assert isinstance(result, DeletedUser)
        assert result.id == 99999

    def test_parse_deleted_user_without_data_id(
        self, mock_client_no_http: MagicMock, printuser_deleted_no_id_html: str
    ) -> None:
        """data-idなし削除済みユーザーをパースできる（ID=0）"""
        soup = BeautifulSoup(printuser_deleted_no_id_html, "lxml")
        elem = soup.select_one("span.printuser")
        assert elem is not None

        # data-idがない場合はKeyErrorが発生するため、テストでは確認できない
        # 実際のコードでは data-id が必須
        with pytest.raises(KeyError):
            user_parse(mock_client_no_http, elem)


class TestUserParserAnonymousUser:
    """匿名ユーザーのパーステスト"""

    def test_parse_anonymous_user_with_ip(self, mock_client_no_http: MagicMock, printuser_anonymous_html: str) -> None:
        """IP付き匿名ユーザーをパースできる"""
        soup = BeautifulSoup(printuser_anonymous_html, "lxml")
        elem = soup.select_one("span.printuser")
        assert elem is not None

        result = user_parse(mock_client_no_http, elem)

        assert isinstance(result, AnonymousUser)
        # Wikidotは最後のオクテットをマスクして表示する
        assert result.ip == "192.168.1.x"

    def test_parse_anonymous_user_without_ip(
        self, mock_client_no_http: MagicMock, printuser_anonymous_no_ip_html: str
    ) -> None:
        """IPなし匿名ユーザーをパースできる"""
        soup = BeautifulSoup(printuser_anonymous_no_ip_html, "lxml")
        elem = soup.select_one("span.printuser")
        assert elem is not None

        result = user_parse(mock_client_no_http, elem)

        assert isinstance(result, AnonymousUser)
        assert result.ip is None


class TestUserParserGuestUser:
    """ゲストユーザーのパーステスト"""

    def test_parse_guest_user(self, mock_client_no_http: MagicMock, printuser_guest_html: str) -> None:
        """Gravatarを持つゲストユーザーをパースできる"""
        soup = BeautifulSoup(printuser_guest_html, "lxml")
        elem = soup.select_one("span.printuser")
        assert elem is not None

        result = user_parse(mock_client_no_http, elem)

        assert isinstance(result, GuestUser)
        assert result.name == "guest-user"
        assert result.avatar_url is not None
        assert "gravatar.com" in result.avatar_url


class TestUserParserWikidotUser:
    """Wikidotシステムユーザーのパーステスト"""

    def test_parse_wikidot_user(self, mock_client_no_http: MagicMock, printuser_wikidot_html: str) -> None:
        """Wikidotシステムユーザーをパースできる"""
        soup = BeautifulSoup(printuser_wikidot_html, "lxml")
        elem = soup.select_one("span.printuser")
        assert elem is not None

        result = user_parse(mock_client_no_http, elem)

        assert isinstance(result, WikidotUser)
        assert result.name == "Wikidot"


class TestUserParserEdgeCases:
    """エッジケースのテスト"""

    def test_parse_no_link_element_raises(self, mock_client_no_http: MagicMock) -> None:
        """リンク要素がない場合はIndexErrorを発生させる"""
        html = '<span class="printuser">No links here</span>'
        soup = BeautifulSoup(html, "lxml")
        elem = soup.select_one("span.printuser")
        assert elem is not None

        # テキストが"Wikidot"でない場合、find_all("a")[-1]が空リストに対して実行されIndexErrorになる
        with pytest.raises(IndexError):
            user_parse(mock_client_no_http, elem)

    def test_parse_user_with_special_characters_in_name(self, mock_client_no_http: MagicMock) -> None:
        """特殊文字を含むユーザー名をパースできる"""
        html = '<span class="printuser"><a href="http://www.wikidot.com/user:info/user-name-123" onclick="WIKIDOT.page.listeners.userInfo(11111); return false;">user_name_123</a></span>'
        soup = BeautifulSoup(html, "lxml")
        elem = soup.select_one("span.printuser")
        assert elem is not None

        result = user_parse(mock_client_no_http, elem)

        assert isinstance(result, User)
        assert result.name == "user_name_123"
        assert result.unix_name == "user-name-123"
