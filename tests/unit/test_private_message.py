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
    Contact,
    PrivateMessage,
    PrivateMessageCollection,
    PrivateMessageInbox,
    PrivateMessageSentBox,
    SiteJoinApplication,
    add_contact,
    add_contact_via_profile,
    get_application_detail_html,
    get_applications,
    get_contacts,
    get_contacts_list_html,
    get_invitation_detail_html,
    get_invitations_html,
    remove_contact,
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

    def test_save_draft_without_recipient_omits_to_user_id(self, mock_client):
        """recipient未指定時はto_user_idキーが送られない"""
        PrivateMessage.save_draft(mock_client, "subj", "body")

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["event"] == "saveDraft"
        assert "to_user_id" not in call_args

    def test_save_draft_with_recipient(self, mock_client, mock_user):
        PrivateMessage.save_draft(mock_client, "subj", "body", mock_user)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["to_user_id"] == mock_user.id

    def test_check_can_send(self, mock_client, mock_user):
        PrivateMessage.check_can_send(mock_client, mock_user)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["action"] == "DashboardMessageAction"
        assert call_args["event"] == "checkCan"
        assert call_args["userId"] == mock_user.id

    def test_preview(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<p>preview</p>"}
        mock_client.amc_client.request.return_value = [mock_response]

        result = PrivateMessage.preview(mock_client, "subj", "body")

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["moduleName"] == "dashboard/messages/DMPreviewModule"
        assert result == "<p>preview</p>"

    def test_fetch_reply_form_html(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<form></form>"}
        mock_client.amc_client.request.return_value = [mock_response]

        result = PrivateMessage.fetch_reply_form_html(mock_client, 555)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["moduleName"] == "dashboard/messages/DMNewMessageModule"
        assert call_args["replyMessageId"] == 555
        assert result == "<form></form>"

    def test_mark_as_read_instance_method(self, sample_message, mock_client):
        sample_message.client = mock_client
        sample_message.mark_as_read()

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["event"] == "setAsReaded"
        assert call_args["selected"] == [sample_message.id]

    def test_mark_as_unread_instance_method(self, sample_message, mock_client):
        sample_message.client = mock_client
        sample_message.mark_as_unread()

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["event"] == "setAsUnreaded"

    def test_delete_instance_method(self, sample_message, mock_client):
        sample_message.client = mock_client
        sample_message.delete()

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["event"] == "removeMessages"
        assert call_args["messages"] == [sample_message.id]


class TestPrivateMessageCollectionBulkOperations:
    """PrivateMessageCollectionのメッセージ一括操作のテスト"""

    def test_mark_as_read_uses_selected_key(self, mock_client):
        """setAsReadedはselected[]で送られる（messages[]ではない）"""
        PrivateMessageCollection.mark_as_read(mock_client, [1, 2, 3])

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["action"] == "DashboardMessageAction"
        assert call_args["event"] == "setAsReaded"
        assert call_args["selected"] == [1, 2, 3]

    def test_mark_as_unread_uses_selected_key(self, mock_client):
        PrivateMessageCollection.mark_as_unread(mock_client, [1, 2])

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["event"] == "setAsUnreaded"
        assert call_args["selected"] == [1, 2]

    def test_remove_messages_uses_messages_key(self, mock_client):
        """removeMessagesはmessages[]で送られる（selected[]ではない）"""
        PrivateMessageCollection.remove_messages(mock_client, [4, 5])

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["event"] == "removeMessages"
        assert call_args["messages"] == [4, 5]

    def test_remove_messages_requires_login(self, mock_client):
        mock_client.is_logged_in = False
        mock_client.login_check.side_effect = LoginRequiredException("Not logged in")

        with pytest.raises(LoginRequiredException):
            PrivateMessageCollection.remove_messages(mock_client, [1])


class TestInvitationsApplicationsContacts:
    """招待・申請・連絡先系のモジュール関数のテスト"""

    def test_get_invitations_html(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div>invitations</div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        result = get_invitations_html(mock_client)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["moduleName"] == "dashboard/messages/DMInvitationsModule"
        assert result == "<div>invitations</div>"

    def test_get_invitation_detail_html(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div>detail</div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        get_invitation_detail_html(mock_client, 9)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["moduleName"] == "dashboard/messages/DMViewInvitationModule"
        assert call_args["item"] == 9

    def test_get_applications_parses_rows(self, mock_client):
        """DMApplicationsModuleの行マークアップ（2026-07-29実測）に基づくfixture"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "body": """
            <table>
            <tr class="message" data-href="#/applications/463303">
                <td>
                    <span class="from">Foo Site</span>
                    <span class="subject">Membership application</span>
                    <span class="preview">Please let me join!</span>
                    <span class="date"><span class="odate time_1700000000">01 Jan 2024</span></span>
                </td>
            </tr>
            </table>
            """
        }
        mock_client.amc_client.request.return_value = [mock_response]

        result = get_applications(mock_client)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["moduleName"] == "dashboard/messages/DMApplicationsModule"
        assert len(result) == 1
        application = result[0]
        assert isinstance(application, SiteJoinApplication)
        assert application.item_id == 463303
        assert application.from_site == "Foo Site"
        assert application.subject == "Membership application"
        assert application.preview == "Please let me join!"
        assert application.submitted_at == datetime.fromtimestamp(1700000000)

    def test_get_applications_skips_rows_without_from(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "body": '<table><tr class="message" data-href="#/applications/1"><td>no from span here</td></tr></table>'
        }
        mock_client.amc_client.request.return_value = [mock_response]

        result = get_applications(mock_client)

        assert result == []

    def test_get_applications_skips_rows_without_data_href(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "body": '<table><tr class="message"><td><span class="from">Foo</span></td></tr></table>'
        }
        mock_client.amc_client.request.return_value = [mock_response]

        result = get_applications(mock_client)

        assert result == []

    def test_site_join_application_fetch_detail_html(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div>detail</div>"}
        mock_client.amc_client.request.return_value = [mock_response]
        application = SiteJoinApplication(
            client=mock_client,
            item_id=463303,
            from_site="Foo Site",
            subject="Membership application",
            preview="Please let me join!",
            submitted_at=datetime.fromtimestamp(1700000000),
        )

        result = application.fetch_detail_html()

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["moduleName"] == "dashboard/messages/DMViewApplicationModule"
        assert call_args["item"] == 463303
        assert result == "<div>detail</div>"

    def test_get_application_detail_html(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div>detail</div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        get_application_detail_html(mock_client, 3)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["moduleName"] == "dashboard/messages/DMViewApplicationModule"
        assert call_args["item"] == 3

    def test_get_contacts_parses_rows(self, mock_client):
        """DMContactsModuleの行マークアップ（2026-07-29実測）に基づくfixture"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "body": """
            <table>
            <tr>
                <td>
                    <span class="printuser avatarhover">
                        <a href="http://www.wikidot.com/user:info/contact-user"
                           onclick="WIKIDOT.page.listeners.userInfo(54321); return false;">contact-user</a>
                    </span>
                </td>
                <td><a class="awesome red small" href="#">x</a></td>
            </tr>
            </table>
            """
        }
        mock_client.amc_client.request.return_value = [mock_response]

        result = get_contacts(mock_client)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["moduleName"] == "dashboard/messages/DMContactsModule"
        assert len(result) == 1
        contact = result[0]
        assert isinstance(contact, Contact)
        assert contact.user.id == 54321
        assert contact.user.name == "contact-user"

    def test_contact_remove_delegates_to_remove_contact(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "body": """
            <span class="printuser avatarhover">
                <a href="http://www.wikidot.com/user:info/contact-user"
                   onclick="WIKIDOT.page.listeners.userInfo(54321); return false;">contact-user</a>
            </span>
            """
        }
        mock_client.amc_client.request.return_value = [mock_response]
        user = MagicMock(id=54321)
        contact = Contact(client=mock_client, user=user)

        contact.remove()

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["action"] == "ContactsAction"
        assert call_args["event"] == "removeContact"
        assert call_args["userId"] == 54321

    def test_get_contacts_list_html(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div>picker</div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        get_contacts_list_html(mock_client)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["moduleName"] == "dashboard/messages/DMContactsListModule"

    def test_add_contact(self, mock_client, mock_user):
        add_contact(mock_client, mock_user)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["action"] == "ContactsAction"
        assert call_args["event"] == "addContact"
        assert call_args["userId"] == mock_user.id

    def test_remove_contact(self, mock_client, mock_user):
        remove_contact(mock_client, mock_user)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["action"] == "ContactsAction"
        assert call_args["event"] == "removeContact"

    def test_add_contact_via_profile(self, mock_client, mock_user):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div>added</div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        result = add_contact_via_profile(mock_client, mock_user)

        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["moduleName"] == "userinfo/UserAddToContactsModule"
        assert call_args["userId"] == mock_user.id
        assert result == "<div>added</div>"
