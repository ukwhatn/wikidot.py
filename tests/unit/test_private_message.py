"""
プライベートメッセージモジュールのユニットテスト

PrivateMessage, PrivateMessageCollection, PrivateMessageInbox, PrivateMessageSentBoxクラスをテストする。
"""

from datetime import datetime
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from wikidot.common.exceptions import ForbiddenException, LoginRequiredException
from wikidot.module.client import Client
from wikidot.module.private_message import (
    PrivateMessage,
    PrivateMessageCollection,
    PrivateMessageInbox,
    PrivateMessageSentBox,
)


@pytest.fixture
def mock_client():
    """モッククライアント（Clientのspec付き）"""
    client = create_autospec(Client, instance=True)
    client.is_logged_in = True
    client.amc_client = MagicMock()
    return client


@pytest.fixture
def mock_user():
    """モックユーザー"""
    user = MagicMock()
    user.id = 12345
    user.name = "test-user"
    return user


@pytest.fixture
def sample_message(mock_client, mock_user):
    """サンプルメッセージ"""
    return PrivateMessage(
        client=mock_client,
        id=1,
        sender=mock_user,
        recipient=mock_user,
        subject="Test Subject",
        body="Test Body",
        created_at=datetime(2023, 1, 1, 12, 0, 0),
    )


class TestPrivateMessageCollection:
    """PrivateMessageCollectionクラスのテスト"""

    def test_str_representation(self, sample_message):
        """文字列表現のテスト"""
        collection = PrivateMessageCollection([sample_message])
        assert "1 messages" in str(collection)

    def test_iter(self, sample_message):
        """イテレータのテスト"""
        collection = PrivateMessageCollection([sample_message])
        messages = list(collection)
        assert len(messages) == 1
        assert messages[0] == sample_message

    def test_find_existing(self, sample_message):
        """存在するメッセージの検索"""
        collection = PrivateMessageCollection([sample_message])
        result = collection.find(1)
        assert result == sample_message

    def test_find_not_existing(self, sample_message):
        """存在しないメッセージの検索"""
        collection = PrivateMessageCollection([sample_message])
        result = collection.find(999)
        assert result is None

    def test_from_ids_requires_login(self, mock_client):
        """from_idsはログインが必要"""
        mock_client.is_logged_in = False
        mock_client.login_check.side_effect = LoginRequiredException("Not logged in")

        with pytest.raises(LoginRequiredException):
            PrivateMessageCollection.from_ids(mock_client, [1, 2, 3])

    def test_from_ids_success(self, mock_client):
        """from_idsの成功ケース"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "body": """
            <div class="pmessage">
                <div class="header">
                    <span class="printuser"><a href="http://www.wikidot.com/user:info/sender" onclick="WIKIDOT.page.listeners.userInfo(11111); return false;">sender</a></span>
                    <span class="printuser"><a href="http://www.wikidot.com/user:info/recipient" onclick="WIKIDOT.page.listeners.userInfo(22222); return false;">recipient</a></span>
                    <span class="subject">Test Subject</span>
                    <span class="odate time_1234567890">01 Jan 2023 12:00</span>
                </div>
                <div class="body">Test Body</div>
            </div>
            """
        }

        mock_client.amc_client.request.return_value = [mock_response]

        with patch("wikidot.module.private_message.user_parser") as mock_user_parser:
            mock_user_parser.return_value = MagicMock()
            with patch("wikidot.module.private_message.odate_parser") as mock_odate_parser:
                mock_odate_parser.return_value = datetime(2023, 1, 1, 12, 0, 0)

                result = PrivateMessageCollection.from_ids(mock_client, [1])

                assert len(result) == 1
                assert result[0].id == 1

    def test_from_ids_forbidden_error(self, mock_client):
        """from_idsでアクセス権限エラー"""
        from wikidot.common.exceptions import WikidotStatusCodeException

        mock_exception = WikidotStatusCodeException("no_message", "No message found")
        mock_exception.status_code = "no_message"

        mock_client.amc_client.request.return_value = [mock_exception]

        with pytest.raises(ForbiddenException):
            PrivateMessageCollection.from_ids(mock_client, [1])


class TestPrivateMessageInbox:
    """PrivateMessageInboxクラスのテスト"""

    def test_from_ids(self, mock_client):
        """from_idsのテスト"""
        with patch.object(
            PrivateMessageCollection, "from_ids", return_value=PrivateMessageCollection([])
        ) as mock_from_ids:
            result = PrivateMessageInbox.from_ids(mock_client, [1, 2])

            mock_from_ids.assert_called_once_with(mock_client, [1, 2])
            assert isinstance(result, PrivateMessageInbox)

    def test_acquire(self, mock_client):
        """acquireのテスト"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div class='pager'></div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        with patch.object(PrivateMessageCollection, "from_ids", return_value=PrivateMessageCollection([])):
            result = PrivateMessageInbox.acquire(mock_client)

            assert isinstance(result, PrivateMessageInbox)


class TestPrivateMessageSentBox:
    """PrivateMessageSentBoxクラスのテスト"""

    def test_from_ids(self, mock_client):
        """from_idsのテスト"""
        with patch.object(
            PrivateMessageCollection, "from_ids", return_value=PrivateMessageCollection([])
        ) as mock_from_ids:
            result = PrivateMessageSentBox.from_ids(mock_client, [1, 2])

            mock_from_ids.assert_called_once_with(mock_client, [1, 2])
            assert isinstance(result, PrivateMessageSentBox)

    def test_acquire(self, mock_client):
        """acquireのテスト"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div class='pager'></div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        with patch.object(PrivateMessageCollection, "from_ids", return_value=PrivateMessageCollection([])):
            result = PrivateMessageSentBox.acquire(mock_client)

            assert isinstance(result, PrivateMessageSentBox)


class TestPrivateMessage:
    """PrivateMessageクラスのテスト"""

    def test_str_representation(self, sample_message):
        """文字列表現のテスト"""
        result = str(sample_message)
        assert "PrivateMessage(" in result
        assert "id=1" in result

    def test_from_id(self, mock_client):
        """from_idのテスト"""
        with patch.object(
            PrivateMessageCollection,
            "from_ids",
            return_value=PrivateMessageCollection([MagicMock()]),
        ) as mock_from_ids:
            result = PrivateMessage.from_id(mock_client, 123)

            mock_from_ids.assert_called_once_with(mock_client, [123])
            assert result is not None

    def test_send_requires_login(self, mock_client, mock_user):
        """sendはログインが必要"""
        mock_client.is_logged_in = False
        mock_client.login_check.side_effect = LoginRequiredException("Not logged in")

        with pytest.raises(LoginRequiredException):
            PrivateMessage.send(mock_client, mock_user, "subject", "body")

    def test_send_success(self, mock_client, mock_user):
        """送信成功"""
        PrivateMessage.send(mock_client, mock_user, "Test Subject", "Test Body")

        mock_client.amc_client.request.assert_called_once()
        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["source"] == "Test Body"
        assert call_args["subject"] == "Test Subject"
        assert call_args["to_user_id"] == mock_user.id
        assert call_args["event"] == "send"
