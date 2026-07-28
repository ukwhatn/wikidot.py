"""
Clientモジュールのユニットテスト

Client, ClientUserAccessor, ClientPrivateMessageAccessor, ClientSiteAccessorクラスをテストする。
"""

from unittest.mock import MagicMock, patch

import pytest

from wikidot.common.exceptions import LoginRequiredException
from wikidot.module.client import (
    Client,
    ClientAccountAccessor,
    ClientPrivateMessageAccessor,
    ClientSiteAccessor,
    ClientUserAccessor,
)


class TestClient:
    """Clientクラスのテスト"""

    def test_init_without_credentials(self):
        """認証情報なしでの初期化"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            assert client.is_logged_in is False
            assert client.username is None

    def test_init_with_credentials(self):
        """認証情報ありでの初期化"""
        with (
            patch("wikidot.module.client.AjaxModuleConnectorClient"),
            patch("wikidot.module.client.HTTPAuthentication.login") as mock_login,
            patch("wikidot.module.client.User.from_name") as mock_from_name,
        ):
            mock_from_name.return_value = MagicMock()
            client = Client(username="test-user", password="test-password")

            mock_login.assert_called_once()
            assert client.is_logged_in is True
            assert client.username == "test-user"

    def test_context_manager_protocol(self):
        """with文でのコンテキストマネージャプロトコル"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"), Client() as client:
            assert isinstance(client, Client)

    def test_context_manager_cleanup_on_exit(self):
        """with文終了時にクリーンアップが呼ばれる"""
        with (
            patch("wikidot.module.client.AjaxModuleConnectorClient"),
            patch("wikidot.module.client.HTTPAuthentication.login"),
            patch("wikidot.module.client.HTTPAuthentication.logout") as mock_logout,
            patch("wikidot.module.client.User.from_name") as mock_from_name,
        ):
            mock_from_name.return_value = MagicMock()
            with Client(username="test-user", password="test-password"):
                pass

            mock_logout.assert_called_once()

    def test_login_check_raises_when_not_logged_in(self):
        """未ログイン時にlogin_checkが例外を送出する"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with pytest.raises(LoginRequiredException):
                client.login_check()

    def test_login_check_passes_when_logged_in(self):
        """ログイン時にlogin_checkが例外を送出しない"""
        with (
            patch("wikidot.module.client.AjaxModuleConnectorClient"),
            patch("wikidot.module.client.HTTPAuthentication.login"),
            patch("wikidot.module.client.User.from_name") as mock_from_name,
        ):
            mock_from_name.return_value = MagicMock()
            client = Client(username="test-user", password="test-password")
            # 例外が送出されないことを確認
            client.login_check()

    def test_str_representation(self):
        """文字列表現のテスト"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            assert "Client(" in str(client)
            assert "is_logged_in=False" in str(client)

    def test_close_called_only_when_logged_in(self):
        """close()はログイン時のみログアウトを呼ぶ"""
        with (
            patch("wikidot.module.client.AjaxModuleConnectorClient"),
            patch("wikidot.module.client.HTTPAuthentication.logout") as mock_logout,
        ):
            client = Client()
            client.close()
            mock_logout.assert_not_called()

        with (
            patch("wikidot.module.client.AjaxModuleConnectorClient"),
            patch("wikidot.module.client.HTTPAuthentication.login"),
            patch("wikidot.module.client.HTTPAuthentication.logout") as mock_logout,
            patch("wikidot.module.client.User.from_name") as mock_from_name,
        ):
            mock_from_name.return_value = MagicMock()
            client = Client(username="test-user", password="test-password")
            client.close()
            mock_logout.assert_called_once()

    def test_accessors_are_initialized(self):
        """各アクセサが初期化される"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            assert isinstance(client.user, ClientUserAccessor)
            assert isinstance(client.private_message, ClientPrivateMessageAccessor)
            assert isinstance(client.site, ClientSiteAccessor)
            assert isinstance(client.account, ClientAccountAccessor)


class TestClientUserAccessor:
    """ClientUserAccessorクラスのテスト"""

    def test_get_user_by_name(self):
        """ユーザー名からユーザーを取得する"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.User.from_name") as mock_from_name:
                mock_user = MagicMock()
                mock_from_name.return_value = mock_user

                result = client.user.get("test-user")

                mock_from_name.assert_called_once_with(client, "test-user", False)
                assert result == mock_user

    def test_get_user_by_name_with_raise(self):
        """ユーザーが見つからない場合に例外を送出"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.User.from_name") as mock_from_name:
                mock_from_name.return_value = None

                result = client.user.get("unknown-user", raise_when_not_found=True)

                mock_from_name.assert_called_once_with(client, "unknown-user", True)
                assert result is None

    def test_get_bulk_users(self):
        """複数ユーザーを一括取得"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.UserCollection.from_names") as mock_from_names:
                mock_collection = MagicMock()
                mock_from_names.return_value = mock_collection

                result = client.user.get_bulk(["user1", "user2"])

                mock_from_names.assert_called_once_with(client, ["user1", "user2"], False)
                assert result == mock_collection


class TestClientPrivateMessageAccessor:
    """ClientPrivateMessageAccessorクラスのテスト"""

    def test_send_message(self):
        """メッセージ送信"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessage.send") as mock_send:
                mock_recipient = MagicMock()
                client.private_message.send(mock_recipient, "subject", "body")

                mock_send.assert_called_once_with(client, mock_recipient, "subject", "body")

    def test_get_inbox(self):
        """受信箱取得"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessageInbox.acquire") as mock_acquire:
                mock_inbox = MagicMock()
                mock_acquire.return_value = mock_inbox

                result = client.private_message.inbox

                mock_acquire.assert_called_once_with(client)
                assert result == mock_inbox

    def test_get_sentbox(self):
        """送信箱取得"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessageSentBox.acquire") as mock_acquire:
                mock_sentbox = MagicMock()
                mock_acquire.return_value = mock_sentbox

                result = client.private_message.sentbox

                mock_acquire.assert_called_once_with(client)
                assert result == mock_sentbox

    def test_get_messages(self):
        """メッセージ一括取得"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessageCollection.from_ids") as mock_from_ids:
                mock_collection = MagicMock()
                mock_from_ids.return_value = mock_collection

                result = client.private_message.get_messages([1, 2, 3])

                mock_from_ids.assert_called_once_with(client, [1, 2, 3])
                assert result == mock_collection

    def test_get_message(self):
        """単一メッセージ取得"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessage.from_id") as mock_from_id:
                mock_message = MagicMock()
                mock_from_id.return_value = mock_message

                result = client.private_message.get_message(123)

                mock_from_id.assert_called_once_with(client, 123)
                assert result == mock_message


class TestClientSiteAccessor:
    """ClientSiteAccessorクラスのテスト"""

    def test_get_site_by_unix_name(self):
        """UNIX名からサイトを取得"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.Site.from_unix_name") as mock_from_unix_name:
                mock_site = MagicMock()
                mock_from_unix_name.return_value = mock_site

                result = client.site.get("scp-wiki")

                mock_from_unix_name.assert_called_once_with(client, "scp-wiki")
                assert result == mock_site

    def test_create_site(self):
        """サイト作成"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.DashboardSites.create") as mock_create:
                mock_create.return_value = "new-site"

                result = client.site.create(name="New Site", unixname="new-site")

                mock_create.assert_called_once_with(
                    client,
                    name="New Site",
                    unixname="new-site",
                    subtitle="",
                    language="en",
                    template="standard-template",
                    privacy="open",
                    tos=True,
                )
                assert result == "new-site"

    def test_my_sites_html(self):
        """サイト一覧の取得"""
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.DashboardSites.list_html") as mock_list_html:
                mock_list_html.return_value = "<div>sites</div>"

                result = client.site.my_sites_html

                mock_list_html.assert_called_once_with(client)
                assert result == "<div>sites</div>"

    def test_accept_invitation(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.DashboardSites.accept_invitation") as mock_accept:
                client.site.accept_invitation(42)
                mock_accept.assert_called_once_with(client, 42)

    def test_throw_away_invitation(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.DashboardSites.throw_away_invitation") as mock_throw:
                client.site.throw_away_invitation(42)
                mock_throw.assert_called_once_with(client, 42)

    def test_remove_application(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.DashboardSites.remove_application") as mock_remove:
                client.site.remove_application(7)
                mock_remove.assert_called_once_with(client, 7)

    def test_restore_site(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.DashboardSites.restore_site") as mock_restore:
                client.site.restore_site(10, "my-site")
                mock_restore.assert_called_once_with(client, 10, "my-site")

    def test_resign_as_admin(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.DashboardSites.resign_as_admin") as mock_resign:
                client.site.resign_as_admin(10)
                mock_resign.assert_called_once_with(client, 10)

    def test_resign_as_moderator(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.DashboardSites.resign_as_moderator") as mock_resign:
                client.site.resign_as_moderator(10)
                mock_resign.assert_called_once_with(client, 10)

    def test_sign_off_as_member(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.DashboardSites.sign_off_as_member") as mock_sign_off:
                client.site.sign_off_as_member(10)
                mock_sign_off.assert_called_once_with(client, 10)

    def test_set_site_storage_limit(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.DashboardSites.set_storage_limit") as mock_set_limit:
                client.site.set_site_storage_limit(10, {"limit": "500"})
                mock_set_limit.assert_called_once_with(client, 10, {"limit": "500"})


class TestClientPrivateMessageAccessorExtensions:
    """ClientPrivateMessageAccessorの拡張メソッド（P5）のテスト"""

    def test_mark_as_read(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessageCollection.mark_as_read") as mock_mark:
                client.private_message.mark_as_read([1, 2])
                mock_mark.assert_called_once_with(client, [1, 2])

    def test_mark_as_unread(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessageCollection.mark_as_unread") as mock_mark:
                client.private_message.mark_as_unread([1, 2])
                mock_mark.assert_called_once_with(client, [1, 2])

    def test_remove(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessageCollection.remove_messages") as mock_remove:
                client.private_message.remove([1, 2])
                mock_remove.assert_called_once_with(client, [1, 2])

    def test_save_draft(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessage.save_draft") as mock_save:
                client.private_message.save_draft("subj", "body")
                mock_save.assert_called_once_with(client, "subj", "body", None)

    def test_check_can_send(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessage.check_can_send") as mock_check:
                mock_user = MagicMock()
                client.private_message.check_can_send(mock_user)
                mock_check.assert_called_once_with(client, mock_user)

    def test_preview(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessage.preview") as mock_preview:
                mock_preview.return_value = "<p>html</p>"
                result = client.private_message.preview("subj", "body")
                mock_preview.assert_called_once_with(client, "subj", "body", None)
                assert result == "<p>html</p>"

    def test_fetch_reply_form_html(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.PrivateMessage.fetch_reply_form_html") as mock_fetch:
                mock_fetch.return_value = "<form></form>"
                result = client.private_message.fetch_reply_form_html(9)
                mock_fetch.assert_called_once_with(client, 9)
                assert result == "<form></form>"

    def test_add_contact(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.pm.add_contact") as mock_add:
                mock_user = MagicMock()
                client.private_message.add_contact(mock_user)
                mock_add.assert_called_once_with(client, mock_user)

    def test_remove_contact(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.pm.remove_contact") as mock_remove:
                mock_user = MagicMock()
                client.private_message.remove_contact(mock_user)
                mock_remove.assert_called_once_with(client, mock_user)

    def test_get_invitations_html(self):
        with patch("wikidot.module.client.AjaxModuleConnectorClient"):
            client = Client()
            with patch("wikidot.module.client.pm.get_invitations_html") as mock_get:
                mock_get.return_value = "<div></div>"
                result = client.private_message.get_invitations_html()
                mock_get.assert_called_once_with(client, 1)
                assert result == "<div></div>"
