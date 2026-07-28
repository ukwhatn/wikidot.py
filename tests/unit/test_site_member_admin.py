"""MemberAccessor（site.member）のユニットテスト"""

from unittest.mock import MagicMock, patch

from wikidot.module.site_block import IpBlock, UserBlock
from wikidot.module.site_member_admin import MemberAccessor, UserSearchResult, _user_id


class TestUserId:
    """_user_id ヘルパのテスト"""

    def test_int_passthrough(self):
        assert _user_id(42) == 42

    def test_user_object(self):
        user = MagicMock()
        user.id = 42
        assert _user_id(user) == 42


class TestGetPaginated:
    """管理ビューの一覧取得（Task 2-1）のテスト"""

    def test_single_page(self):
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

        accessor = MemberAccessor(site)
        with patch("wikidot.module.site_member.user_parser") as mock_user_parser:
            mock_user_parser.return_value = MagicMock()
            members = accessor.get_members()

        assert len(members) == 1
        call_body = site.amc_request.call_args[0][0][0]
        assert call_body["moduleName"] == "managesite/members/ManageSiteMembersListModule"
        assert call_body["page"] == 1

    def test_pagination(self):
        site = MagicMock()
        first_response = MagicMock()
        first_response.json.return_value = {
            "body": """
                <table><tr><td><span class="printuser">
                    <a onclick="WIKIDOT.page.listeners.userInfo(1)" href="#">User1</a>
                </span></td></tr></table>
                <div class="pager"><a href="#">1</a><a href="#">2</a><a href="#">next</a></div>
            """
        }
        second_response = MagicMock()
        second_response.json.return_value = {
            "body": """
                <table><tr><td><span class="printuser">
                    <a onclick="WIKIDOT.page.listeners.userInfo(2)" href="#">User2</a>
                </span></td></tr></table>
            """
        }
        site.amc_request.side_effect = [[first_response], [second_response]]

        accessor = MemberAccessor(site)
        with patch("wikidot.module.site_member.user_parser") as mock_user_parser:
            mock_user_parser.return_value = MagicMock()
            moderators = accessor.get_moderators()

        assert len(moderators) == 2
        assert site.amc_request.call_count == 2

    def test_get_admins_uses_admins_module(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"body": "<table></table>"}
        site.amc_request.return_value = [response]

        MemberAccessor(site).get_admins()

        call_body = site.amc_request.call_args[0][0][0]
        assert call_body["moduleName"] == "managesite/members/ManageSiteAdminsModule"


class TestRemoveAndChangeMaster:
    """Task 2-2: removeMember / changeMaster / moderator permissions"""

    def test_remove_without_ban_omits_key(self):
        site = MagicMock()
        MemberAccessor(site).remove(42)

        body = site.amc_request.call_args[0][0][0]
        assert body["action"] == "ManageSiteMembershipAction"
        assert body["event"] == "removeMember"
        assert body["user_id"] == 42
        assert "ban" not in body

    def test_remove_with_ban_sends_yes(self):
        site = MagicMock()
        MemberAccessor(site).remove(42, ban=True)

        body = site.amc_request.call_args[0][0][0]
        assert body["ban"] == "yes"

    def test_change_master_uses_camel_case_userid(self):
        site = MagicMock()
        MemberAccessor(site).change_master(99)

        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "changeMaster"
        assert body["userId"] == 99
        assert "user_id" not in body

    def test_get_moderator_permissions_form_returns_raw_body(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"body": "<form>raw</form>"}
        site.amc_request.return_value = [response]

        result = MemberAccessor(site).get_moderator_permissions_form(7)

        assert result == {"body": "<form>raw</form>"}
        call_body = site.amc_request.call_args[0][0][0]
        assert call_body["moduleName"] == "managesite/ManageSiteModeratorPermissionsModule"
        assert call_body["moderatorId"] == 7

    def test_save_moderator_permissions_passes_fields_verbatim(self):
        site = MagicMock()
        MemberAccessor(site).save_moderator_permissions(foo="bar", baz=1)

        body = site.amc_request.call_args[0][0][0]
        assert body["action"] == "ManageSiteMembershipAction"
        assert body["event"] == "saveModeratorPermissions"
        assert body["foo"] == "bar"
        assert body["baz"] == 1


class TestInvitations:
    """Task 2-4: 招待"""

    def test_search_users_zips_ids_and_names(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"userIds": [1, 2], "userNames": ["a", "b"]}
        site.amc_request.return_value = [response]

        results = MemberAccessor(site).search_users("a")

        assert results == [UserSearchResult(id=1, name="a"), UserSearchResult(id=2, name="b")]

    def test_send_email_invitations_encodes_addresses_as_json_array_of_arrays(self):
        site = MagicMock()
        MemberAccessor(site).send_email_invitations([("a@example.com", "A", True)], message="hi")

        body = site.amc_request.call_args[0][0][0]
        assert body["addresses"] == '[["a@example.com", "A", true]]'
        assert body["message"] == "hi"

    def test_delete_email_invitation(self):
        site = MagicMock()
        MemberAccessor(site).delete_email_invitation(123)

        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "deleteEmailInvitation"
        assert body["invitationId"] == 123

    def test_resend_email_invitation(self):
        site = MagicMock()
        MemberAccessor(site).resend_email_invitation(123, message="again")

        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "resendEmailInvitation"
        assert body["invitationId"] == 123
        assert body["message"] == "again"

    def test_set_let_users_invite_always_sends_string_bool(self):
        site = MagicMock()
        MemberAccessor(site).set_let_users_invite(False)

        body = site.amc_request.call_args[0][0][0]
        assert body["enableLetUsersInvite"] == "false"

    def test_invite_admin_returns_user_id(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"result": "invited", "userId": 55}
        site.amc_request.return_value = [response]

        result = MemberAccessor(site).invite_admin(55)

        assert result == 55
        body = site.amc_request.call_args[0][0][0]
        assert body["action"] == "ManageSiteAction"
        assert body["event"] == "inviteAdmin"
        assert body["user_id"] == 55


class TestBlocks:
    """Task 2-5: ブロック"""

    def test_get_blocked_users_parses_rows(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {
            "body": """
                <table><tr>
                    <td><span class="printuser">
                        <a onclick="WIKIDOT.page.listeners.userInfo(1)" href="#">U1</a>
                    </span></td>
                    <td>spam</td>
                </tr></table>
            """
        }
        site.amc_request.return_value = [response]

        with patch("wikidot.module.site_block.user_parser") as mock_user_parser:
            mock_user_parser.return_value = MagicMock()
            blocks = MemberAccessor(site).get_blocked_users()

        assert len(blocks) == 1
        assert isinstance(blocks[0], UserBlock)
        assert blocks[0].reason == "spam"
        call_body = site.amc_request.call_args[0][0][0]
        assert call_body["moduleName"] == "managesite/blocks/ManageSiteUserBlocksModule"

    def test_get_blocked_ips_extracts_block_id_from_onclick(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {
            "body": """
                <table><tr>
                    <td>1.2.3.4</td>
                    <td>
                        <a onclick="WIKIDOT.modules.ManageSiteIpBlocksModule.listeners.deleteBlock(event, 999, 'x')">unblock</a>
                    </td>
                    <td>abuse</td>
                </tr></table>
            """
        }
        site.amc_request.return_value = [response]

        blocks = MemberAccessor(site).get_blocked_ips()

        assert len(blocks) == 1
        assert isinstance(blocks[0], IpBlock)
        assert blocks[0].block_id == 999
        assert blocks[0].ip == "1.2.3.4"
        assert blocks[0].reason == "abuse"

    def test_block_user(self):
        site = MagicMock()
        MemberAccessor(site).block_user(1, reason="spam")

        body = site.amc_request.call_args[0][0][0]
        assert body["action"] == "ManageSiteBlockAction"
        assert body["event"] == "blockUser"
        assert body["userId"] == 1
        assert body["reason"] == "spam"

    def test_unblock_user_uses_user_id_not_block_id(self):
        site = MagicMock()
        MemberAccessor(site).unblock_user(1)

        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "deleteBlock"
        assert body["userId"] == 1

    def test_block_ip(self):
        site = MagicMock()
        MemberAccessor(site).block_ip("1.2.3.4", reason="abuse")

        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "blockIp"
        assert body["ips"] == "1.2.3.4"

    def test_unblock_ip_uses_block_id_not_user_id(self):
        site = MagicMock()
        MemberAccessor(site).unblock_ip(999)

        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "deleteIpBlock"
        assert body["blockId"] == 999
        assert "userId" not in body


class TestAbuseAndWatching:
    """Task 2-6: フラグ解除・自動監視・ブロックリンク"""

    def test_clear_user_flags(self):
        site = MagicMock()
        MemberAccessor(site).clear_user_flags(1)

        body = site.amc_request.call_args[0][0][0]
        assert body["action"] == "ManageSiteAbuseAction"
        assert body["event"] == "clearUserFlags"
        assert body["userId"] == 1

    def test_clear_page_flags(self):
        site = MagicMock()
        MemberAccessor(site).clear_page_flags("component:scp-173")

        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "clearPageFlags"
        assert body["path"] == "component:scp-173"

    def test_clear_anonymous_flags_without_proxy_omits_key(self):
        site = MagicMock()
        MemberAccessor(site).clear_anonymous_flags("1.2.3.4")

        body = site.amc_request.call_args[0][0][0]
        assert body["address"] == "1.2.3.4"
        assert "proxy" not in body

    def test_clear_anonymous_flags_with_proxy_sends_yes(self):
        site = MagicMock()
        MemberAccessor(site).clear_anonymous_flags("1.2.3.4", proxy=True)

        body = site.amc_request.call_args[0][0][0]
        assert body["proxy"] == "yes"

    def test_set_members_watching_with_categories(self):
        site = MagicMock()
        MemberAccessor(site).set_members_watching(watch_all=False, selected_categories=[1, 2])

        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "saveMembersWatching"
        assert body["selected_categories"] == [1, 2]
        assert "watch_all" not in body

    def test_set_members_watching_watch_all(self):
        site = MagicMock()
        MemberAccessor(site).set_members_watching(watch_all=True)

        body = site.amc_request.call_args[0][0][0]
        assert body["watch_all"] == "on"

    def test_set_block_link(self):
        site = MagicMock()
        MemberAccessor(site).set_block_link(3, block_link=True)

        body = site.amc_request.call_args[0][0][0]
        assert body["action"] == "ManageSiteAction"
        assert body["event"] == "saveBlockLink"
        assert body["karmaLevel"] == 3
        assert body["blockLink"] == "true"
