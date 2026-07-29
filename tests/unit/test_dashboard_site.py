"""
Dashboard のサイト操作モジュール（module.dashboard_site）のユニットテスト

DashboardSitesクラスをテストする。
"""

from unittest.mock import MagicMock, create_autospec

import pytest

from wikidot.common.exceptions import LoginRequiredException
from wikidot.module.client import Client
from wikidot.module.dashboard_site import DashboardSite, DashboardSites


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


#: DSListModule row fixture, based on the 2026-07-29 markup measurement
#: recorded in 70_account.md ("一覧モジュールの行マークアップ")
DS_LIST_MODULE_BODY = """
<div class="site">
  <a class="thumbnail-site" href="http://foo.wikidot.com">
    <img class="thumbnail-site" src="http://foo.wikidot.com/local--files/favicon/foo.png" />
  </a>
  <div class="name"><a href="http://foo.wikidot.com">Foo Site</a></div>
  <div class="url">http://foo.wikidot.com</div>
  <a class="btn" href="/account/sites#/manage/123456">Manage</a>
  <div class="data">
    <span class="activity">12</span>
    <span class="site-id">123456</span>
    <span class="unix-name">foo</span>
    <span class="tagline">A test site</span>
    <span class="occupation">admin</span>
  </div>
</div>
<div class="site">
  <div class="name"><a href="http://bar.wikidot.com">Bar Site</a></div>
  <div class="url">http://bar.wikidot.com</div>
  <div class="data">
    <span class="activity">0</span>
    <span class="site-id">654321</span>
    <span class="unix-name">bar</span>
    <span class="tagline"></span>
    <span class="occupation">member</span>
    <span class="deleted"></span>
  </div>
</div>
"""


class TestDashboardSiteAcquireAll:
    """DashboardSite.acquire_all / DashboardSites.list_sites のテスト"""

    def test_parses_all_rows(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": DS_LIST_MODULE_BODY}
        mock_client.amc_client.request.return_value = [mock_response]

        result = DashboardSites.list_sites(mock_client)

        body = _last_body(mock_client)
        assert body["moduleName"] == "dashboard/sites/DSListModule"
        assert len(result) == 2

    def test_active_site_fields(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": DS_LIST_MODULE_BODY}
        mock_client.amc_client.request.return_value = [mock_response]

        result = DashboardSites.list_sites(mock_client)
        site = result[0]

        assert isinstance(site, DashboardSite)
        assert site.site_id == 123456
        assert site.title == "Foo Site"
        assert site.url == "http://foo.wikidot.com"
        assert site.unix_name == "foo"
        assert site.tagline == "A test site"
        assert site.role == "admin"
        assert site.deleted is False

    def test_deleted_site_fields(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": DS_LIST_MODULE_BODY}
        mock_client.amc_client.request.return_value = [mock_response]

        result = DashboardSites.list_sites(mock_client)
        site = result[1]

        assert site.site_id == 654321
        assert site.role == "member"
        assert site.deleted is True

    def test_row_actions_delegate_to_dashboard_sites(self, mock_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": DS_LIST_MODULE_BODY}
        mock_client.amc_client.request.return_value = [mock_response]

        site = DashboardSites.list_sites(mock_client)[0]
        mock_client.amc_client.request.reset_mock()

        site.resign_as_admin()

        body = _last_body(mock_client)
        assert body["event"] == "adminResign"
        assert body["site_id"] == 123456
