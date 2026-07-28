"""site_settingsモジュールのユニットテスト"""

from unittest.mock import MagicMock

import pytest

from wikidot.common.exceptions import FormErrorsException
from wikidot.module.site_category import SiteCategoryCollection, SiteLicense
from wikidot.module.site_permissions import PagePermissions, RatingSettings
from wikidot.module.site_settings import SiteSettingsAccessor


def _make_site(categories_response: dict | None = None) -> MagicMock:
    """categories 応答を返す amc_request を積んだ MagicMock の Site"""
    site = MagicMock()
    if categories_response is not None:
        fetch_response = MagicMock()
        fetch_response.json.return_value = categories_response
        # 1回目=fetch, 2回目=save のレスポンスとして両方同じMagicMockでよい
        site.amc_request.return_value = [fetch_response]
    return site


class TestUpdateCategories:
    """update_categoriesが毎回fetch->mutate->saveの順で呼ばれること"""

    def test_fetch_then_save_two_requests(self, site_categories_single):
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        called = []

        def mutator(cats: SiteCategoryCollection) -> None:
            called.append(cats["_default"].category_id)

        accessor.update_categories("ManageSiteAction", "savePermissions", mutator)

        assert called == [30228632]
        assert site.amc_request.call_count == 2
        fetch_call, save_call = site.amc_request.call_args_list
        assert fetch_call[0][0] == [{"moduleName": "managesite/ManageSitePermissionsModule"}]
        save_body = save_call[0][0][0]
        assert save_body["action"] == "ManageSiteAction"
        assert save_body["event"] == "savePermissions"

    def test_no_caching_refetches_every_call(self, site_categories_single):
        # 2回呼べば2回ともfetchされること（キャッシュされていないこと）
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        accessor.update_categories("ManageSiteAction", "savePermissions", lambda cats: None)
        accessor.update_categories("ManageSiteAction", "saveLicense", lambda cats: None)

        assert site.amc_request.call_count == 4  # fetch+save が2セット


class TestPermissions:
    def test_set_page_permissions_clears_default_flag(self, site_categories_single):
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)
        new_perms = PagePermissions.decode("v:arm;c:m;e:m;m:m;d:m;a:m;r:m;z:m;o:m")

        accessor.set_page_permissions("_default", new_perms)

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["event"] == "savePermissions"
        assert "v:arm" in save_body["categories"]

    def test_use_default_page_permissions(self, site_categories_single):
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        accessor.use_default_page_permissions("_default")

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert (
            '"permissions_default": true' in save_body["categories"]
            or '"permissions_default":true' in save_body["categories"]
        )

    def test_category_not_found_propagates_keyerror(self, site_categories_single):
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        with pytest.raises(KeyError):
            accessor.set_page_permissions("nonexistent", PagePermissions())


class TestLicense:
    def test_set_license(self, site_categories_single):
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        accessor.set_license("_default", SiteLicense.CC_ATTRIBUTION_3_0)

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["event"] == "saveLicense"
        assert '"license_id": 13' in save_body["categories"] or '"license_id":13' in save_body["categories"]

    def test_other_without_text_raises(self, site_categories_single):
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        with pytest.raises(ValueError, match="license_other"):
            accessor.set_license("_default", SiteLicense.OTHER)

    def test_other_with_text_ok(self, site_categories_single):
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        accessor.set_license("_default", SiteLicense.OTHER, other="My custom license")

        assert site.amc_request.call_count == 2


class TestNavigationTemplatesPageRatePerPageDiscussionAppearance:
    def test_set_navigation(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_navigation("_default", "nav:top", "nav:side2")
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["event"] == "saveNavigation"

    def test_set_template(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_template("_default", 42)
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["event"] == "saveTemplates"
        assert '"template_id": 42' in save_body["categories"] or '"template_id":42' in save_body["categories"]

    def test_set_page_rate_settings(self, site_categories_single):
        site = _make_site(site_categories_single)
        rating = RatingSettings.decode("emaS")
        SiteSettingsAccessor(site).set_page_rate_settings("_default", rating)
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["event"] == "savePageRateSettings"

    def test_set_per_page_discussion_explicit(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_per_page_discussion("_default", False)
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["action"] == "ManageSiteForumAction"
        assert save_body["event"] == "savePerPageDiscussion"

    def test_set_per_page_discussion_default(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_per_page_discussion("_default", None)
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert '"per_page_discussion_default": true' in save_body["categories"] or (
            '"per_page_discussion_default":true' in save_body["categories"]
        )

    def test_set_appearance_theme(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_appearance_theme("_default", 7)
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["action"] == "ManageSiteThemeAction"
        assert save_body["event"] == "saveAppearance"

    def test_set_appearance_external_theme_sends_empty_string_theme_id(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_appearance_external_theme("_default", "https://example.com/theme.css")
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert '"theme_id": ""' in save_body["categories"] or '"theme_id":""' in save_body["categories"]


class TestGeneralDomainAccessPolicy:
    def test_save_general_success_no_unixname(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok", "CURRENT_TIMESTAMP": 1785204323, "callbackIndex": None}
        site.amc_request.return_value = [response]

        result = SiteSettingsAccessor(site).save_general(name="Test Site")

        assert result is None
        body = site.amc_request.call_args[0][0][0]
        assert body["action"] == "ManageSiteAction"
        assert body["event"] == "saveGeneral"
        assert body["name"] == "Test Site"

    def test_save_general_returns_new_unixname(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok", "unixName": "new-name"}
        site.amc_request.return_value = [response]

        result = SiteSettingsAccessor(site).save_general(name="Test Site")

        assert result == "new-name"

    def test_save_general_empty_name_raises_form_errors(self):
        site = MagicMock()
        site.amc_request.side_effect = FormErrorsException(
            "form_errors",
            "form_errors",
            {
                "status": "form_errors",
                "formErrors": {"name": "Please provide the site title", "defaultPage": "..."},
                "message": "Form errors",
            },
        )

        with pytest.raises(FormErrorsException) as exc_info:
            SiteSettingsAccessor(site).save_general(name="")

        assert exc_info.value.errors["name"] == "Please provide the site title"

    def test_save_domain_too_many_redirects_raises(self):
        site = MagicMock()
        with pytest.raises(ValueError, match="10"):
            SiteSettingsAccessor(site).save_domain("example.com", redirects=[f"r{i}.com" for i in range(11)])

    def test_save_domain_joins_redirects_with_semicolon(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok"}
        site.amc_request.return_value = [response]

        SiteSettingsAccessor(site).save_domain("example.com", redirects=["a.com", "b.com"])

        body = site.amc_request.call_args[0][0][0]
        assert body["redirects"] == "a.com;b.com"

    def test_save_access_policy_viewers_from_ids(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok"}
        site.amc_request.return_value = [response]

        SiteSettingsAccessor(site).save_access_policy("private", viewers=[111, 222])

        body = site.amc_request.call_args[0][0][0]
        assert body["viewers"] == "111,222"
        assert body["privacy"] == "private"

    def test_save_access_policy_omits_unchecked_checkboxes(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok"}
        site.amc_request.return_value = [response]

        SiteSettingsAccessor(site).save_access_policy("open")

        body = site.amc_request.call_args[0][0][0]
        assert "by_apply" not in body
        assert "allowHotlink" not in body


class TestSingleShotSettings:
    def _response(self, site: MagicMock, payload: dict | None = None) -> None:
        response = MagicMock()
        response.json.return_value = payload or {"status": "ok"}
        site.amc_request.return_value = [response]

    def test_save_custom_footer_omits_use_when_false(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).save_custom_footer("footer text")
        body = site.amc_request.call_args[0][0][0]
        assert body["source"] == "footer text"
        assert "use" not in body

    def test_save_custom_footer_sends_use_true(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).save_custom_footer("footer text", use=True)
        body = site.amc_request.call_args[0][0][0]
        assert body["use"] == "true"

    def test_save_toolbars_preference(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).save_toolbars_preference(toolbar_top=True)
        body = site.amc_request.call_args[0][0][0]
        assert body["toolbarTop"] == "on"
        assert "toolbarBottom" not in body

    def test_save_api_settings_uses_dashed_keys(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).save_api_settings(enabled=True, read_1=True)
        body = site.amc_request.call_args[0][0][0]
        assert body["sm-api-enable"] == "on"
        assert body["read-1"] == "on"
        assert "write-1" not in body

    def test_add_autonumeration(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).add_autonumeration("_default", override=True)
        body = site.amc_request.call_args[0][0][0]
        assert body["categoryName"] == "_default"
        assert body["override"] == "true"

    def test_add_pingbacks_without_override_omits_key(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).add_pingbacks("_default")
        body = site.amc_request.call_args[0][0][0]
        assert "override" not in body

    def test_save_openid_always_sends_enable_flag(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).save_openid(False)
        body = site.amc_request.call_args[0][0][0]
        assert body["enableOpenID"] == "false"

    def test_request_backup(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).request_backup(backup_sources=True, backup_type="tar")
        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "requestBackup"
        assert body["backupSources"] == "on"
        assert body["backupType"] == "tar"

    def test_delete_backup_requires_confirm(self):
        site = MagicMock()
        with pytest.raises(ValueError, match="confirm"):
            SiteSettingsAccessor(site).delete_backup(confirm=False)

    def test_delete_backup_with_confirm_sends_request(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).delete_backup(confirm=True)
        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "deleteBackup"

    def test_set_windows_icon_background_color_uses_exact_typo_event_name(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).set_windows_icon_background_color("#ffffff")
        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "windowsIconBackroundColor"

    def test_preview_newsletter(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok", "title": "Rendered", "content": "<p>hi</p>"}
        site.amc_request.return_value = [response]

        title, content = SiteSettingsAccessor(site).preview_newsletter("T", "C")

        assert title == "Rendered"
        assert content == "<p>hi</p>"

    def test_send_newsletter_others_as_list_for_bracket_encoding(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).send_newsletter("T", "C", admins=True, others=[1, 2, 3])
        body = site.amc_request.call_args[0][0][0]
        assert body["admins"] == "true"
        assert body["moderators"] == "false"
        assert body["others"] == [1, 2, 3]

    def test_send_newsletter_others_empty_by_default(self):
        site = MagicMock()
        self._response(site)
        SiteSettingsAccessor(site).send_newsletter("T", "C")
        body = site.amc_request.call_args[0][0][0]
        assert body["others"] == []
