"""SiteMemberモジュールのユニットテスト"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from wikidot.common.exceptions import TargetErrorException, WikidotStatusCodeException
from wikidot.module.site_member import SiteMember


class TestSiteMemberDataclass:
    """SiteMemberデータクラスのテスト"""

    def test_init(self):
        """初期化のテスト"""
        site = MagicMock()
        user = MagicMock()
        joined_at = datetime.now(timezone.utc)

        member = SiteMember(site=site, user=user, joined_at=joined_at)

        assert member.site == site
        assert member.user == user
        assert member.joined_at == joined_at

    def test_init_without_joined_at(self):
        """joined_atなしでの初期化"""
        site = MagicMock()
        user = MagicMock()

        member = SiteMember(site=site, user=user, joined_at=None)

        assert member.joined_at is None


class TestSiteMemberParse:
    """SiteMember._parseのテスト"""

    def test_parse_single_member(self):
        """1人のメンバーをパース"""
        html = BeautifulSoup(
            """
            <table>
                <tr>
                    <td><span class="printuser">
                        <a onclick="WIKIDOT.page.listeners.userInfo(12345)" href="#">Test User</a>
                    </span></td>
                    <td><span class="odate time_123456789">2024-01-01</span></td>
                </tr>
            </table>
            """,
            "lxml",
        )
        site = MagicMock()
        mock_user = MagicMock()

        with (
            patch("wikidot.module.site_member.user_parser") as mock_user_parser,
            patch("wikidot.module.site_member.odate_parser") as mock_odate_parser,
        ):
            mock_user_parser.return_value = mock_user
            mock_odate_parser.return_value = datetime(2024, 1, 1, tzinfo=timezone.utc)

            members = SiteMember._parse(site, html)

            assert len(members) == 1
            assert members[0].site == site
            assert members[0].user == mock_user
            assert members[0].joined_at == datetime(2024, 1, 1, tzinfo=timezone.utc)

    def test_parse_member_without_joined_at(self):
        """joined_atなしのメンバーをパース"""
        html = BeautifulSoup(
            """
            <table>
                <tr>
                    <td><span class="printuser">
                        <a onclick="WIKIDOT.page.listeners.userInfo(12345)" href="#">Test User</a>
                    </span></td>
                </tr>
            </table>
            """,
            "lxml",
        )
        site = MagicMock()
        mock_user = MagicMock()

        with patch("wikidot.module.site_member.user_parser") as mock_user_parser:
            mock_user_parser.return_value = mock_user

            members = SiteMember._parse(site, html)

            assert len(members) == 1
            assert members[0].joined_at is None

    def test_parse_skips_rows_without_printuser(self):
        """printuserがない行はスキップ"""
        html = BeautifulSoup(
            """
            <table>
                <tr>
                    <td>Header</td>
                </tr>
                <tr>
                    <td><span class="printuser">
                        <a onclick="WIKIDOT.page.listeners.userInfo(12345)" href="#">Test User</a>
                    </span></td>
                </tr>
            </table>
            """,
            "lxml",
        )
        site = MagicMock()
        mock_user = MagicMock()

        with patch("wikidot.module.site_member.user_parser") as mock_user_parser:
            mock_user_parser.return_value = mock_user

            members = SiteMember._parse(site, html)

            assert len(members) == 1


class TestSiteMemberGet:
    """SiteMember.getのテスト"""

    def test_get_members_single_page(self):
        """単一ページのメンバー取得"""
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {
            "body": """
                <table>
                    <tr>
                        <td><span class="printuser">
                            <a onclick="WIKIDOT.page.listeners.userInfo(12345)" href="#">User1</a>
                        </span></td>
                    </tr>
                </table>
            """
        }
        site.amc_request.return_value = [response]

        with patch("wikidot.module.site_member.user_parser") as mock_user_parser:
            mock_user_parser.return_value = MagicMock()

            members = SiteMember.get(site, "")

            assert len(members) == 1
            site.amc_request.assert_called_once()

    def test_get_members_with_pagination(self):
        """ページネーション付きのメンバー取得"""
        site = MagicMock()

        first_response = MagicMock()
        first_response.json.return_value = {
            "body": """
                <table>
                    <tr>
                        <td><span class="printuser">
                            <a onclick="WIKIDOT.page.listeners.userInfo(12345)" href="#">User1</a>
                        </span></td>
                    </tr>
                </table>
                <div class="pager">
                    <a href="#">1</a>
                    <a href="#">2</a>
                    <a href="#">next</a>
                </div>
            """
        }

        second_response = MagicMock()
        second_response.json.return_value = {
            "body": """
                <table>
                    <tr>
                        <td><span class="printuser">
                            <a onclick="WIKIDOT.page.listeners.userInfo(67890)" href="#">User2</a>
                        </span></td>
                    </tr>
                </table>
            """
        }

        site.amc_request.side_effect = [[first_response], [second_response]]

        with patch("wikidot.module.site_member.user_parser") as mock_user_parser:
            mock_user_parser.return_value = MagicMock()

            members = SiteMember.get(site, "")

            assert len(members) == 2
            assert site.amc_request.call_count == 2

    def test_get_admins_group(self):
        """管理者グループ取得"""
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"body": "<table></table>"}
        site.amc_request.return_value = [response]

        SiteMember.get(site, "admins")

        call_args = site.amc_request.call_args[0][0][0]
        assert call_args["group"] == "admins"

    def test_get_moderators_group(self):
        """モデレーターグループ取得"""
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"body": "<table></table>"}
        site.amc_request.return_value = [response]

        SiteMember.get(site, "moderators")

        call_args = site.amc_request.call_args[0][0][0]
        assert call_args["group"] == "moderators"

    def test_get_invalid_group_raises(self):
        """無効なグループでValueError"""
        site = MagicMock()

        with pytest.raises(ValueError, match="Invalid group"):
            SiteMember.get(site, "invalid_group")

    def test_get_default_group(self):
        """デフォルトグループ（None）"""
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"body": "<table></table>"}
        site.amc_request.return_value = [response]

        SiteMember.get(site, None)

        call_args = site.amc_request.call_args[0][0][0]
        assert call_args["group"] == ""


class TestSiteMemberChangeGroup:
    """SiteMember._change_groupのテスト"""

    def test_to_moderator_success(self):
        """モデレーター昇格成功"""
        site = MagicMock()
        user = MagicMock()
        user.id = 12345
        member = SiteMember(site=site, user=user, joined_at=None)

        member.to_moderator()

        call_args = site.amc_request.call_args[0][0][0]
        assert call_args["action"] == "ManageSiteMembershipAction"
        assert call_args["event"] == "toModerators"
        assert call_args["user_id"] == 12345

    def test_remove_moderator_success(self):
        """モデレーター降格成功"""
        site = MagicMock()
        user = MagicMock()
        user.id = 12345
        member = SiteMember(site=site, user=user, joined_at=None)

        member.remove_moderator()

        call_args = site.amc_request.call_args[0][0][0]
        assert call_args["event"] == "removeModerator"

    def test_to_admin_success(self):
        """管理者昇格成功"""
        site = MagicMock()
        user = MagicMock()
        user.id = 12345
        member = SiteMember(site=site, user=user, joined_at=None)

        member.to_admin()

        call_args = site.amc_request.call_args[0][0][0]
        assert call_args["event"] == "toAdmins"

    def test_remove_admin_success(self):
        """管理者降格成功"""
        site = MagicMock()
        user = MagicMock()
        user.id = 12345
        member = SiteMember(site=site, user=user, joined_at=None)

        member.remove_admin()

        call_args = site.amc_request.call_args[0][0][0]
        assert call_args["event"] == "removeAdmin"

    def test_change_group_already_moderator_error(self):
        """既にモデレーターの場合のエラー"""
        site = MagicMock()
        user = MagicMock()
        user.id = 12345
        user.name = "TestUser"
        member = SiteMember(site=site, user=user, joined_at=None)

        site.amc_request.side_effect = WikidotStatusCodeException(
            "already_moderator",
            "already_moderator",
        )

        with pytest.raises(TargetErrorException, match="already moderator"):
            member.to_moderator()

    def test_change_group_already_admin_error(self):
        """既に管理者の場合のエラー"""
        site = MagicMock()
        user = MagicMock()
        user.id = 12345
        user.name = "TestUser"
        member = SiteMember(site=site, user=user, joined_at=None)

        site.amc_request.side_effect = WikidotStatusCodeException(
            "already_admin",
            "already_admin",
        )

        with pytest.raises(TargetErrorException, match="already admin"):
            member.to_admin()

    def test_change_group_not_already_error(self):
        """権限を持っていない場合のエラー"""
        site = MagicMock()
        user = MagicMock()
        user.id = 12345
        user.name = "TestUser"
        member = SiteMember(site=site, user=user, joined_at=None)

        site.amc_request.side_effect = WikidotStatusCodeException(
            "not_already",
            "not_already",
        )

        with pytest.raises(TargetErrorException, match="not moderator/admin"):
            member.remove_moderator()

    def test_change_group_invalid_event_raises(self):
        """無効なイベントでValueError"""
        site = MagicMock()
        user = MagicMock()
        member = SiteMember(site=site, user=user, joined_at=None)

        with pytest.raises(ValueError, match="Invalid event"):
            member._change_group("invalidEvent")

    def test_change_group_other_error_reraises(self):
        """その他のエラーは再送出"""
        site = MagicMock()
        user = MagicMock()
        user.id = 12345
        member = SiteMember(site=site, user=user, joined_at=None)

        site.amc_request.side_effect = WikidotStatusCodeException(
            "some_other_error",
            "some_other_error",
        )

        with pytest.raises(WikidotStatusCodeException):
            member.to_moderator()
