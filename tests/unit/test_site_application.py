"""SiteApplicationモジュールのユニットテスト"""

from unittest.mock import MagicMock, create_autospec, patch

import pytest

from wikidot.common.exceptions import (
    ForbiddenException,
    LoginRequiredException,
    NotFoundException,
    UnexpectedException,
    WikidotStatusCodeException,
)
from wikidot.module.client import Client
from wikidot.module.site_application import SiteApplication


def create_mock_client(is_logged_in: bool = True) -> MagicMock:
    """Clientクラスのモックを作成（isinstance()チェックを通過する）"""
    mock_client = create_autospec(Client, instance=True)
    mock_client.is_logged_in = is_logged_in
    if is_logged_in:
        mock_client.login_check.return_value = None
    else:
        mock_client.login_check.side_effect = LoginRequiredException("Login required")
    return mock_client


class TestSiteApplicationDataclass:
    """SiteApplicationデータクラスのテスト"""

    def test_init(self):
        """初期化"""
        site = MagicMock()
        user = MagicMock()

        app = SiteApplication(site=site, user=user, text="Please let me join")

        assert app.site == site
        assert app.user == user
        assert app.text == "Please let me join"

    def test_str(self):
        """文字列表現"""
        site = MagicMock()
        site.__str__ = lambda x: "TestSite"
        user = MagicMock()
        user.__str__ = lambda x: "TestUser"

        app = SiteApplication(site=site, user=user, text="Application text")

        result = str(app)
        assert "SiteApplication" in result
        assert "user=" in result
        assert "site=" in result
        assert "text=" in result


class TestSiteApplicationAcquireAll:
    """SiteApplication.acquire_allのテスト"""

    def test_acquire_all_success(self):
        """申請リスト取得成功"""
        mock_client = create_mock_client(is_logged_in=True)
        site = MagicMock()
        site.client = mock_client

        response = MagicMock()
        response.json.return_value = {
            "body": """
                <div>
                    <h3><span class="printuser">
                        <a onclick="WIKIDOT.page.listeners.userInfo(12345)" href="#">User1</a>
                    </span></h3>
                    <table>
                        <tr>
                            <td>Label</td>
                            <td>I want to join this wiki</td>
                        </tr>
                    </table>
                </div>
            """
        }
        site.amc_request.return_value = [response]

        with patch("wikidot.module.site_application.user_parser") as mock_user_parser:
            mock_user = MagicMock()
            mock_user_parser.return_value = mock_user

            applications = SiteApplication.acquire_all(site)

            assert len(applications) == 1
            assert applications[0].user == mock_user
            assert applications[0].text == "I want to join this wiki"

    def test_acquire_all_empty(self):
        """申請なしの場合"""
        mock_client = create_mock_client(is_logged_in=True)
        site = MagicMock()
        site.client = mock_client

        response = MagicMock()
        response.json.return_value = {"body": "<div>No applications</div>"}
        site.amc_request.return_value = [response]

        applications = SiteApplication.acquire_all(site)

        assert len(applications) == 0

    def test_acquire_all_forbidden(self):
        """権限がない場合ForbiddenException"""
        mock_client = create_mock_client(is_logged_in=True)
        site = MagicMock()
        site.client = mock_client

        response = MagicMock()
        response.json.return_value = {"body": '<a onclick="WIKIDOT.page.listeners.loginClick(event)">Login</a>'}
        site.amc_request.return_value = [response]

        with pytest.raises(ForbiddenException, match="not allowed"):
            SiteApplication.acquire_all(site)

    def test_acquire_all_not_logged_in(self):
        """未ログインでLoginRequiredException"""
        mock_client = create_mock_client(is_logged_in=False)
        site = MagicMock()
        site.client = mock_client

        with pytest.raises(LoginRequiredException):
            SiteApplication.acquire_all(site)

    def test_acquire_all_length_mismatch(self):
        """ユーザー要素とテキスト要素の数が不一致でUnexpectedException"""
        mock_client = create_mock_client(is_logged_in=True)
        site = MagicMock()
        site.client = mock_client

        response = MagicMock()
        response.json.return_value = {
            "body": """
                <div>
                    <h3><span class="printuser">
                        <a onclick="WIKIDOT.page.listeners.userInfo(12345)" href="#">User1</a>
                    </span></h3>
                    <h3><span class="printuser">
                        <a onclick="WIKIDOT.page.listeners.userInfo(67890)" href="#">User2</a>
                    </span></h3>
                    <table>
                        <tr>
                            <td>Label</td>
                            <td>Only one table</td>
                        </tr>
                    </table>
                </div>
            """
        }
        site.amc_request.return_value = [response]

        with pytest.raises(UnexpectedException, match="Length"):
            SiteApplication.acquire_all(site)


class TestSiteApplicationProcess:
    """SiteApplication._processのテスト"""

    def test_accept_success(self):
        """承認成功"""
        mock_client = create_mock_client(is_logged_in=True)
        site = MagicMock()
        site.client = mock_client
        user = MagicMock()
        user.id = 12345

        app = SiteApplication(site=site, user=user, text="")
        app.accept()

        call_args = site.amc_request.call_args[0][0][0]
        assert call_args["action"] == "ManageSiteMembershipAction"
        assert call_args["type"] == "accept"
        assert call_args["user_id"] == 12345

    def test_decline_success(self):
        """拒否成功"""
        mock_client = create_mock_client(is_logged_in=True)
        site = MagicMock()
        site.client = mock_client
        user = MagicMock()
        user.id = 12345

        app = SiteApplication(site=site, user=user, text="")
        app.decline()

        call_args = site.amc_request.call_args[0][0][0]
        assert call_args["type"] == "decline"

    def test_process_invalid_action(self):
        """無効なアクションでValueError"""
        mock_client = create_mock_client(is_logged_in=True)
        site = MagicMock()
        site.client = mock_client
        user = MagicMock()

        app = SiteApplication(site=site, user=user, text="")

        with pytest.raises(ValueError, match="Invalid action"):
            app._process("invalid")

    def test_process_not_logged_in(self):
        """未ログインでLoginRequiredException"""
        mock_client = create_mock_client(is_logged_in=False)
        site = MagicMock()
        site.client = mock_client
        user = MagicMock()

        app = SiteApplication(site=site, user=user, text="")

        with pytest.raises(LoginRequiredException):
            app.accept()

    def test_process_application_not_found(self):
        """申請が見つからない場合NotFoundException"""
        mock_client = create_mock_client(is_logged_in=True)
        site = MagicMock()
        site.client = mock_client
        user = MagicMock()
        user.id = 12345
        user.__str__ = lambda x: "TestUser"

        site.amc_request.side_effect = WikidotStatusCodeException(
            "no_application",
            "no_application",
        )

        app = SiteApplication(site=site, user=user, text="")

        with pytest.raises(NotFoundException, match="Application not found"):
            app.accept()

    def test_process_other_error_reraises(self):
        """その他のエラーは再送出"""
        mock_client = create_mock_client(is_logged_in=True)
        site = MagicMock()
        site.client = mock_client
        user = MagicMock()
        user.id = 12345

        site.amc_request.side_effect = WikidotStatusCodeException(
            "other_error",
            "other_error",
        )

        app = SiteApplication(site=site, user=user, text="")

        with pytest.raises(WikidotStatusCodeException):
            app.accept()
