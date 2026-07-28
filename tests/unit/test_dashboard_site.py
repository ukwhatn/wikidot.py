"""
Dashboard のサイト操作モジュール（module.dashboard_site）のユニットテスト

DashboardSitesクラスをテストする。
"""

from unittest.mock import MagicMock, create_autospec

import pytest

from wikidot.common.exceptions import LoginRequiredException
from wikidot.module.client import Client
from wikidot.module.dashboard_site import DashboardSites


@pytest.fixture
def mock_client():
    """モッククライアント（Clientのspec付き）"""
    client = create_autospec(Client, instance=True)
    client.is_logged_in = True
    client.amc_client = MagicMock()
    return client


def _last_body(mock_client):
    """直前のamc_client.request呼び出しの最初のリクエストボディを取得"""
    return mock_client.amc_client.request.call_args[0][0][0]


class TestDashboardSitesCreate:
    """DashboardSites.createのテスト"""

    def test_create_success_returns_unix_name(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "siteUnixName": "my-new-site"}
        mock_client.amc_client.request.return_value = [mock_response]

        result = DashboardSites.create(
            mock_client,
            name="My Site",
            unixname="my-new-site",
        )

        body = _last_body(mock_client)
        assert body["action"] == "NewSiteAction"
        assert body["event"] == "createSite"
        assert body["name"] == "My Site"
        assert body["unixname"] == "my-new-site"
        assert body["tos"] == "on"
        assert result == "my-new-site"

    def test_create_tos_false_omits_key(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"siteUnixName": "x"}
        mock_client.amc_client.request.return_value = [mock_response]

        DashboardSites.create(mock_client, name="X", unixname="x", tos=False)

        body = _last_body(mock_client)
        assert "tos" not in body

    def test_create_requires_login(self, mock_client):
        mock_client.is_logged_in = False
        mock_client.login_check.side_effect = LoginRequiredException("Not logged in")

        with pytest.raises(LoginRequiredException):
            DashboardSites.create(mock_client, name="X", unixname="x")


class TestDashboardSitesInvitationsAndApplications:
    """招待・申請系のテスト"""

    def test_accept_invitation(self, mock_client):
        DashboardSites.accept_invitation(mock_client, 42)

        body = _last_body(mock_client)
        assert body["action"] == "DashboardSitesAction"
        assert body["event"] == "acceptInvitation"
        assert body["invitation_id"] == 42

    def test_throw_away_invitation(self, mock_client):
        DashboardSites.throw_away_invitation(mock_client, 42)

        body = _last_body(mock_client)
        assert body["event"] == "throwAwayInvitation"
        assert body["invitation_id"] == 42

    def test_remove_application(self, mock_client):
        DashboardSites.remove_application(mock_client, 7)

        body = _last_body(mock_client)
        assert body["event"] == "removeApplication"
        assert body["site_id"] == 7


class TestDashboardSitesResignAndRestore:
    """辞任・復元系のテスト"""

    def test_restore_site(self, mock_client):
        DashboardSites.restore_site(mock_client, 10, "my-deleted-site")

        body = _last_body(mock_client)
        assert body["event"] == "restoreSite"
        assert body["site_id"] == 10
        assert body["site_name"] == "my-deleted-site"

    def test_resign_as_admin(self, mock_client):
        DashboardSites.resign_as_admin(mock_client, 10)

        body = _last_body(mock_client)
        assert body["event"] == "adminResign"
        assert body["site_id"] == 10

    def test_resign_as_moderator(self, mock_client):
        DashboardSites.resign_as_moderator(mock_client, 10)

        body = _last_body(mock_client)
        assert body["event"] == "moderatorResign"

    def test_sign_off_as_member(self, mock_client):
        DashboardSites.sign_off_as_member(mock_client, 10)

        body = _last_body(mock_client)
        assert body["event"] == "memberSignOff"

    def test_set_storage_limit_passes_raw_fields(self, mock_client):
        """未実測フォームは生dictをそのまま送る"""
        DashboardSites.set_storage_limit(mock_client, 10, {"limit": "500"})

        body = _last_body(mock_client)
        assert body["event"] == "setStorageLimit"
        assert body["site_id"] == 10
        assert body["limit"] == "500"


class TestDashboardSitesListHtml:
    """list_htmlのテスト"""

    def test_list_html_returns_body(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "<div class='data'>...</div>"}
        mock_client.amc_client.request.return_value = [mock_response]

        result = DashboardSites.list_html(mock_client)

        body = _last_body(mock_client)
        assert body["moduleName"] == "dashboard/sites/DSListModule"
        assert result == "<div class='data'>...</div>"
