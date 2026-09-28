"""
User の user:info タブ取得（module.user_info）のユニットテスト

fixture は 2026-09-28 の実機応答（tests/fixtures/amc_responses/user/）から行数だけ削って作っている。
"""

from datetime import datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from wikidot.common.exceptions import AMCHttpStatusCodeException, NoElementException
from wikidot.module.client import Client
from wikidot.module.user import User


@pytest.fixture
def mock_client():
    """ログインしていないモッククライアント（Clientのspec付き）"""
    client = create_autospec(Client, instance=True)
    client.is_logged_in = False
    client.amc_client = MagicMock()
    return client


@pytest.fixture
def user(mock_client):
    return User(client=mock_client, id=8823243, name="r-4981", unix_name="r-4981")


def _mock_responses(*bodies: dict):
    """複数回のamc_client.request呼び出しに対して、順番にレスポンスを返すside_effectを作る"""
    responses = []
    for body in bodies:
        mock_response = MagicMock()
        mock_response.json.return_value = body
        responses.append([mock_response])
    return responses


def _request_bodies(mock_client):
    return [call[0][0][0] for call in mock_client.amc_client.request.call_args_list]


class TestUserGetChanges:
    def test_sends_user_id_to_list_module_without_login(self, mock_client, user, load_json_fixture):
        """シェルモジュールを経由せず、UserChangesListModuleに他人のuserIdを直接送る"""
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "changes_list_last_of_two.json"),
        )

        user.get_changes()

        body = _request_bodies(mock_client)[0]
        assert body["moduleName"] == "userinfo/UserChangesListModule"
        assert body["userId"] == 8823243
        assert body["page"] == 1
        assert body["perpage"] == 1000
        assert "options" not in body

    def test_parses_full_url_href_as_page_fullname(self, mock_client, user, load_json_fixture):
        """実機のtd.title > aは完全URLなので、パス部分をpage_fullnameにする"""
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "changes_list_last_of_two.json"),
        )

        changes = user.get_changes()

        assert changes[0].site_title == "Redacted Archive."
        assert changes[0].site_url == "https://redacted-archive.wikidot.com"
        assert changes[0].page_fullname == "ait-series"
        assert changes[0].page_title == "研究資料#07 - ヤングAI"
        assert changes[0].revision_no == 10
        assert changes[0].changed_at == datetime.fromtimestamp(1713550160)
        assert changes[0].flags == ["S", "T"]

    def test_new_page_row_has_revision_no_zero(self, mock_client, user, load_json_fixture):
        """revision-noが"(new)"の行（新規作成）はrevision_no=0"""
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "changes_list_last_of_two.json"),
        )

        changes = user.get_changes()

        assert changes[1].page_fullname == "arasame-144"
        assert changes[1].revision_no == 0
        assert changes[1].flags == ["N"]

    def test_follows_pager_until_last_page(self, mock_client, user, load_json_fixture):
        """1/2のpagerでは次へ進み、2/2のpager（« previous, 1 だけ）で終了する"""
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "changes_list_first_of_two.json"),
            load_json_fixture("user", "changes_list_last_of_two.json"),
        )

        changes = user.get_changes()

        assert [body["page"] for body in _request_bodies(mock_client)] == [1, 2]
        assert [c.page_fullname for c in changes] == ["scp-9418", "departments", "ait-series", "arasame-144"]

    def test_stops_at_limit(self, mock_client, user, load_json_fixture):
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "changes_list_first_of_two.json"),
        )

        changes = user.get_changes(limit=1)

        assert len(changes) == 1
        assert _request_bodies(mock_client)[0]["perpage"] == 1

    def test_sends_options_as_json(self, mock_client, user, load_json_fixture):
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "changes_list_empty.json"),
        )

        user.get_changes(options={"new": True})

        assert "options" in _request_bodies(mock_client)[0]

    def test_rejects_unknown_option_before_request(self, mock_client, user):
        with pytest.raises(ValueError, match="tags"):
            user.get_changes(options={"tags": True})
        mock_client.amc_client.request.assert_not_called()

    def test_no_revisions_returns_empty_list(self, mock_client, user, load_json_fixture):
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "changes_list_empty.json"),
        )

        assert user.get_changes() == []


class TestUserGetPosts:
    def test_parses_row_fields(self, mock_client, user, load_json_fixture):
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "posts_list_single.json"),
        )

        posts = user.get_posts()

        body = _request_bodies(mock_client)[0]
        assert body == {"moduleName": "userinfo/UserRecentPostsListModule", "page": 1, "userId": 8823243}
        assert len(posts) == 1
        post = posts[0]
        assert post.title == "Coming up soon:"
        assert post.url == "https://scp-wiki.wikidot.com/scp-9418/comments/show#post-9081419"
        assert post.created_at == datetime.fromtimestamp(1790512849)
        assert post.content.startswith("SCP-10648 - The Aether II")
        assert post.post_id == 9081419
        assert post.site_title == "SCP Foundation"
        assert post.site_url == "https://scp-wiki.wikidot.com"
        assert post.thread_title == "SCP-9418"
        assert post.thread_url == "https://scp-wiki.wikidot.com/scp-9418/comments/show"

    def test_site_and_thread_are_not_taken_from_printuser_link(self, mock_client, user, load_json_fixture):
        """div.info内のprintuserのリンクではなく、"on site"/"in discussion:"直後のリンクを取る"""
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "posts_list_middle.json"),
            load_json_fixture("user", "posts_list_empty.json"),
        )

        post = user.get_posts()[0]

        assert post.post_id == 8597914
        assert post.site_title == "SCP財団"
        assert post.thread_title == "スタッフ/コントリ人員更新のお知らせ"
        assert post.thread_url == "https://scp-jp.wikidot.com/forum/t-14109916/"

    def test_follows_pager_from_middle_page(self, mock_client, user, load_json_fixture):
        """中間ページのpager（« previous, 1, 3, 4, next »）では次へ進み、0件のページで終了する"""
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "posts_list_middle.json"),
            load_json_fixture("user", "posts_list_middle.json"),
            load_json_fixture("user", "posts_list_empty.json"),
        )

        posts = user.get_posts()

        assert [body["page"] for body in _request_bodies(mock_client)] == [1, 2, 3]
        assert len(posts) == 4

    def test_stops_at_limit(self, mock_client, user, load_json_fixture):
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "posts_list_middle.json"),
        )

        assert len(user.get_posts(limit=1)) == 1

    def test_missing_info_links_are_none(self, mock_client, user):
        mock_client.amc_client.request.side_effect = _mock_responses(
            {
                "body": '<div class="post"><div class="long"><div class="head">'
                '<div class="title"><a href="https://example.wikidot.com/forum/t-1">T</a></div>'
                "</div></div></div>"
            },
        )

        post = user.get_posts()[0]

        assert post.post_id is None
        assert post.site_title is None
        assert post.site_url is None
        assert post.thread_title is None
        assert post.thread_url is None

    def test_no_posts_returns_empty_list(self, mock_client, user, load_json_fixture):
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "posts_list_empty.json"),
        )

        assert user.get_posts() == []


class TestUserGetProfile:
    def test_parses_profile_rows(self, mock_client, user, load_json_fixture):
        mock_client.amc_client.request.side_effect = _mock_responses(load_json_fixture("user", "profile.json"))

        profile = user.get_profile()

        body = _request_bodies(mock_client)[0]
        assert body == {"moduleName": "userinfo/UserInfoProfileModule", "user_id": 8823243}
        assert profile.real_name == "或る祝杯"
        assert profile.website == "https://kleismic.com"
        assert profile.member_since == datetime.fromtimestamp(1696412553)
        assert profile.account_type == "free"
        assert profile.karma_level == "high"
        assert profile.fields == {
            "Real name": "或る祝杯",
            "Website": "kleismic.com",
            "Wikidot user since": "04 Oct 2023 09:42",
            "Account type": "free",
            "Karma level": "high (what is this?)",
        }

    def test_missing_rows_are_none(self, mock_client, user):
        mock_client.amc_client.request.side_effect = _mock_responses(
            {
                "body": '<div class="profile-box"><dl class="dl-horizontal"><dt>Account type:</dt><dd> pro </dd></dl></div>'
            }
        )

        profile = user.get_profile()

        assert profile.fields == {"Account type": "pro"}
        assert profile.account_type == "pro"
        assert profile.real_name is None
        assert profile.website is None
        assert profile.member_since is None
        assert profile.karma_level is None

    def test_website_without_link_uses_text(self, mock_client, user):
        mock_client.amc_client.request.side_effect = _mock_responses(
            {"body": '<div class="profile-box"><dl><dt>Website:</dt><dd> example.com </dd></dl></div>'}
        )

        assert user.get_profile().website == "example.com"

    def test_missing_profile_box_raises(self, mock_client, user):
        mock_client.amc_client.request.side_effect = _mock_responses({"body": ""})

        with pytest.raises(NoElementException):
            user.get_profile()

    def test_nonexistent_user_propagates_amc_error(self, mock_client):
        """存在しないuser_idではWikidotがHTTP 500を返し、AMCの例外がそのまま伝わる"""
        mock_client.amc_client.request.side_effect = AMCHttpStatusCodeException("HTTP 500", 500)

        with pytest.raises(AMCHttpStatusCodeException):
            User(client=mock_client, id=999999999).get_profile()


class TestUserGetSiteEntries:
    def test_member_of(self, mock_client, user, load_json_fixture):
        mock_client.amc_client.request.side_effect = _mock_responses(load_json_fixture("user", "member_of.json"))

        entries = user.get_member_of()

        assert _request_bodies(mock_client)[0] == {
            "moduleName": "userinfo/UserInfoMemberOfModule",
            "user_id": 8823243,
        }
        assert [(e.title, e.url, e.subtitle) for e in entries] == [
            ("Redacted Archive.", "https://redacted-archive.wikidot.com", "Secured, Contained, Protected."),
            ("SCP Foundation", "https://scp-wiki.wikidot.com", "Secure, Contain, Protect"),
            ("営利法人 因幡の白兎", "https://moon-rabbit.wikidot.com", "発見、確保、売却"),
        ]
        assert entries[0].description is None
        assert entries[1].description is not None
        assert entries[1].description.startswith("Welcome to the Foundation Database.")

    def test_admin_of(self, mock_client, user, load_json_fixture):
        mock_client.amc_client.request.side_effect = _mock_responses(load_json_fixture("user", "admin_of.json"))

        entries = user.get_admin_of()

        assert _request_bodies(mock_client)[0]["moduleName"] == "userinfo/UserInfoAdminOfModule"
        assert [(e.title, e.url) for e in entries] == [("Redacted Archive.", "https://redacted-archive.wikidot.com")]

    def test_moderator_of_without_list_returns_empty(self, mock_client, user, load_json_fixture):
        """0件のタブにはdlが無く文言だけが出る"""
        mock_client.amc_client.request.side_effect = _mock_responses(
            load_json_fixture("user", "moderator_of_empty.json")
        )

        assert user.get_moderator_of() == []
        assert _request_bodies(mock_client)[0]["moduleName"] == "userinfo/UserInfoModeratorOfModule"

    def test_entry_without_subtitle(self, mock_client, user):
        mock_client.amc_client.request.side_effect = _mock_responses(
            {"body": '<dl><dt><a href="https://a.wikidot.com">A</a></dt><dd></dd></dl>'}
        )

        entry = user.get_member_of()[0]

        assert entry.subtitle is None
        assert entry.description is None

    def test_user_without_id_raises(self, mock_client):
        with pytest.raises(ValueError):
            User(client=mock_client).get_member_of()
