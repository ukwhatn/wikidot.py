"""
アカウント/Dashboardモジュール（module.account）のユニットテスト

AccountSettings, AccountProfile, AccountRecentActivity, ClientAccountAccessorをテストする。
"""

from unittest.mock import MagicMock, create_autospec

import pytest

from wikidot.common.exceptions import LoginRequiredException
from wikidot.module.account import (
    AccountProfile,
    AccountRecentActivity,
    AccountSettings,
    ClientAccountAccessor,
)
from wikidot.module.client import Client


@pytest.fixture
def mock_client():
    """モッククライアント（Clientのspec付き）"""
    client = create_autospec(Client, instance=True)
    client.is_logged_in = True
    client.amc_client = MagicMock()
    client.me = MagicMock(id=99999)
    return client


def _last_body(mock_client):
    """直前のamc_client.request呼び出しの最初のリクエストボディを取得"""
    return mock_client.amc_client.request.call_args[0][0][0]


class TestAccountSettings:
    """AccountSettingsクラスのテスト"""

    def test_set_receive_messages(self, mock_client):
        settings = AccountSettings(mock_client)
        settings.set_receive_messages("mf")

        body = _last_body(mock_client)
        assert body["action"] == "DashboardSettingsAction"
        assert body["event"] == "saveReceiveMessages"
        assert body["from"] == "mf"

    def test_block_user(self, mock_client):
        settings = AccountSettings(mock_client)
        user = MagicMock(id=123)
        settings.block_user(user)

        body = _last_body(mock_client)
        assert body["event"] == "blockUser"
        assert body["userId"] == 123

    def test_unblock_user(self, mock_client):
        settings = AccountSettings(mock_client)
        user = MagicMock(id=123)
        settings.unblock_user(user)

        body = _last_body(mock_client)
        assert body["event"] == "deleteBlock"
        assert body["userId"] == 123

    def test_change_password(self, mock_client):
        settings = AccountSettings(mock_client)
        settings.change_password("old-pw", "new-pw")

        body = _last_body(mock_client)
        assert body["event"] == "changePassword"
        assert body["old_password"] == "old-pw"
        assert body["new_password1"] == "new-pw"
        assert body["new_password2"] == "new-pw"

    def test_set_receive_digest_true_sends_yes(self, mock_client):
        """receive=Trueは"yes"文字列で送られる"""
        settings = AccountSettings(mock_client)
        settings.set_receive_digest(True)

        body = _last_body(mock_client)
        assert body["receive"] == "yes"

    def test_set_receive_digest_false_omits_key(self, mock_client):
        """receive=Falseはキーごと省略される"""
        settings = AccountSettings(mock_client)
        settings.set_receive_digest(False)

        body = _last_body(mock_client)
        assert "receive" not in body

    def test_set_receive_invitations_true_sends_true_string(self, mock_client):
        """saveReceiveInvitationsはreceive="true"（flag形式、"yes"ではない）"""
        settings = AccountSettings(mock_client)
        settings.set_receive_invitations(True)

        body = _last_body(mock_client)
        assert body["receive"] == "true"

    def test_set_toolbars_partial(self, mock_client):
        """未指定側のキーは省略される（チェックボックス省略規則）"""
        settings = AccountSettings(mock_client)
        settings.set_toolbars(top=True, bottom=False)

        body = _last_body(mock_client)
        assert body["toolbarTop"] == "on"
        assert "toolbarBottom" not in body

    def test_generate_api_key_read_only(self, mock_client):
        """read_only=Trueはtype="r"で送られる"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"newKey": "abc123"}
        mock_client.amc_client.request.return_value = [mock_response]

        settings = AccountSettings(mock_client)
        result = settings.generate_api_key(read_only=True)

        body = _last_body(mock_client)
        assert body["type"] == "r"
        assert result == "abc123"

    def test_generate_api_key_read_write(self, mock_client):
        """read_only=Falseはtype="r"以外（"w"）で送られる"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"newKey": "xyz789"}
        mock_client.amc_client.request.return_value = [mock_response]

        settings = AccountSettings(mock_client)
        settings.generate_api_key(read_only=False)

        body = _last_body(mock_client)
        assert body["type"] != "r"

    def test_toolbars_pref_not_confused_with_managesite(self, mock_client):
        """saveToolbarsPrefはDashboardSettingsAction向け（ManageSiteActionではない）"""
        settings = AccountSettings(mock_client)
        settings.set_toolbars(top=True, bottom=True)

        body = _last_body(mock_client)
        assert body["action"] == "DashboardSettingsAction"
        assert body["event"] == "saveToolbarsPref"

    def test_requires_login(self, mock_client):
        mock_client.is_logged_in = False
        mock_client.login_check.side_effect = LoginRequiredException("Not logged in")

        settings = AccountSettings(mock_client)
        with pytest.raises(LoginRequiredException):
            settings.set_language("ja")

    def test_get_messages_html_uses_ds_prefixed_module(self, mock_client):
        """再レンダリングに使うのはdashboard/settings/DSMessagesModule"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div>settings</div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        settings = AccountSettings(mock_client)
        html = settings.get_messages_html()

        body = _last_body(mock_client)
        assert body["moduleName"] == "dashboard/settings/DSMessagesModule"
        assert html == "<div>settings</div>"


class TestAccountProfile:
    """AccountProfileクラスのテスト"""

    def test_change_screen_name(self, mock_client):
        profile = AccountProfile(mock_client)
        profile.change_screen_name("new-name")

        body = _last_body(mock_client)
        assert body["action"] == "DashboardProfileAction"
        assert body["event"] == "changeScreenName"
        assert body["screenName"] == "new-name"

    def test_save_about_omits_unset_gender(self, mock_client):
        profile = AccountProfile(mock_client)
        profile.save_about(real_name="Test User")

        body = _last_body(mock_client)
        assert body["real_name"] == "Test User"
        assert "gender" not in body

    def test_save_forum_signature(self, mock_client):
        profile = AccountProfile(mock_client)
        profile.save_forum_signature("my signature")

        body = _last_body(mock_client)
        assert body["event"] == "saveForumSignature"
        assert body["source"] == "my signature"

    def test_preview_forum_signature(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<p>preview</p>"}
        mock_client.amc_client.request.return_value = [mock_response]

        profile = AccountProfile(mock_client)
        result = profile.preview_forum_signature("sig")

        body = _last_body(mock_client)
        assert body["moduleName"] == "dashboard/settings/DSForumSignaturePreviewModule"
        assert result == "<p>preview</p>"

    def test_delete_avatar(self, mock_client):
        profile = AccountProfile(mock_client)
        profile.delete_avatar()

        body = _last_body(mock_client)
        assert body["event"] == "deleteAvatar"

    def test_upload_avatar_from_uri(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "im48": "u48", "im16": "u16"}
        mock_client.amc_client.request.return_value = [mock_response]

        profile = AccountProfile(mock_client)
        result = profile.upload_avatar_from_uri("http://example.com/a.png")

        body = _last_body(mock_client)
        assert body["uri"] == "http://example.com/a.png"
        assert result["im48"] == "u48"

    def test_save_profile_visibility_passes_raw_fields(self, mock_client):
        """未実測フォームは生dictをそのまま送る"""
        profile = AccountProfile(mock_client)
        profile.save_profile_visibility({"some_field": "value"})

        body = _last_body(mock_client)
        assert body["some_field"] == "value"


class TestAccountRecentActivity:
    """AccountRecentActivityクラスのテスト"""

    def test_get_changes_html_uses_own_user_id(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div>changes</div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        recent = AccountRecentActivity(mock_client)
        html = recent.get_changes_html()

        body = _last_body(mock_client)
        assert body["moduleName"] == "userinfo/UserChangesListModule"
        assert body["userId"] == 99999
        assert html == "<div>changes</div>"

    def test_get_changes_html_rejects_tags_option(self, mock_client):
        """UserChangesListModuleのoptionsに"tags"は存在しない"""
        recent = AccountRecentActivity(mock_client)
        with pytest.raises(ValueError, match="tags"):
            recent.get_changes_html(options={"tags": True})

    def test_get_changes_html_accepts_valid_options(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": ""}
        mock_client.amc_client.request.return_value = [mock_response]

        recent = AccountRecentActivity(mock_client)
        recent.get_changes_html(options={"source": True, "title": True})

        body = _last_body(mock_client)
        assert "options" in body

    def test_get_posts_html_uses_own_user_id(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div>posts</div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        recent = AccountRecentActivity(mock_client)
        recent.get_posts_html()

        body = _last_body(mock_client)
        assert body["moduleName"] == "userinfo/UserRecentPostsListModule"
        assert body["userId"] == 99999


class TestClientAccountAccessor:
    """ClientAccountAccessorクラスのテスト"""

    def test_sub_accessors_initialized(self, mock_client):
        accessor = ClientAccountAccessor(mock_client)

        assert isinstance(accessor.settings, AccountSettings)
        assert isinstance(accessor.profile, AccountProfile)
        assert isinstance(accessor.recent, AccountRecentActivity)
