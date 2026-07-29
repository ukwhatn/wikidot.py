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
    """update_categoriesが指定モジュールから毎回fetch->mutate->saveの順で呼ばれること"""

    def test_fetch_then_save_two_requests(self, site_categories_single):
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        called = []

        def mutator(cats: SiteCategoryCollection) -> None:
            called.append(cats["_default"].category_id)

        accessor.update_categories(
            "managesite/ManageSitePermissionsModule", "ManageSiteAction", "savePermissions", mutator
        )

        assert called == [30228632]
        assert site.amc_request.call_count == 2
        fetch_call, save_call = site.amc_request.call_args_list
        assert fetch_call[0][0] == [{"moduleName": "managesite/ManageSitePermissionsModule"}]
        save_body = save_call[0][0][0]
        assert save_body["action"] == "ManageSiteAction"
        assert save_body["event"] == "savePermissions"

    def test_fetches_from_the_module_name_passed_in(self, site_categories_single):
        # 各領域が自分のモジュールから fetch すること（Permissionsモジュール固定に戻さない）
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        accessor.update_categories(
            "managesite/ManageSiteLicenseModule", "ManageSiteAction", "saveLicense", lambda cats: None
        )

        fetch_call = site.amc_request.call_args_list[0][0][0]
        assert fetch_call == [{"moduleName": "managesite/ManageSiteLicenseModule"}]

    def test_no_caching_refetches_every_call(self, site_categories_single):
        # 2回呼べば2回ともfetchされること（キャッシュされていないこと）
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        accessor.update_categories(
            "managesite/ManageSitePermissionsModule", "ManageSiteAction", "savePermissions", lambda cats: None
        )
        accessor.update_categories(
            "managesite/ManageSiteLicenseModule", "ManageSiteAction", "saveLicense", lambda cats: None
        )

        assert site.amc_request.call_count == 4  # fetch+save が2セット


class TestPermissions:
    def test_set_page_permissions_clears_default_flag(self, site_categories_single):
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)
        new_perms = PagePermissions.decode("v:arm;c:m;e:m;m:m;d:m;a:m;r:m;z:m;o:m")

        accessor.set_page_permissions("_default", new_perms)

        fetch_body = site.amc_request.call_args_list[0][0][0]
        assert fetch_body == [{"moduleName": "managesite/ManageSitePermissionsModule"}]
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
    def test_set_license_fetches_from_license_module(self, site_categories_single):
        site = _make_site(site_categories_single)
        accessor = SiteSettingsAccessor(site)

        accessor.set_license("_default", SiteLicense.CC_ATTRIBUTION_3_0)

        fetch_body = site.amc_request.call_args_list[0][0][0]
        assert fetch_body == [{"moduleName": "managesite/ManageSiteLicenseModule"}]
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
    def test_set_navigation_fetches_from_navigation_module(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_navigation("_default", "nav:top", "nav:side2")
        fetch_body = site.amc_request.call_args_list[0][0][0]
        assert fetch_body == [{"moduleName": "managesite/ManageSiteNavigationModule"}]
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["event"] == "saveNavigation"

    def test_set_template_fetches_from_templates_module(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_template("_default", 42)
        fetch_body = site.amc_request.call_args_list[0][0][0]
        assert fetch_body == [{"moduleName": "managesite/ManageSiteTemplatesModule"}]
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["event"] == "saveTemplates"
        assert '"template_id": 42' in save_body["categories"] or '"template_id":42' in save_body["categories"]

    def test_set_page_rate_settings_fetches_from_pagerate_module(self, site_categories_single):
        site = _make_site(site_categories_single)
        rating = RatingSettings.decode("emaS")
        SiteSettingsAccessor(site).set_page_rate_settings("_default", rating)
        fetch_body = site.amc_request.call_args_list[0][0][0]
        assert fetch_body == [{"moduleName": "managesite/pagerate/ManageSitePageRateSettingsModule"}]
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["event"] == "savePageRateSettings"

    def test_set_per_page_discussion_explicit_fetches_from_perpagediscussion_module(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_per_page_discussion("_default", False)
        fetch_body = site.amc_request.call_args_list[0][0][0]
        assert fetch_body == [{"moduleName": "managesite/ManageSitePerPageDiscussionModule"}]
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

    def test_set_appearance_theme_fetches_from_appearance_module(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_appearance_theme("_default", 7)
        fetch_body = site.amc_request.call_args_list[0][0][0]
        assert fetch_body == [{"moduleName": "managesite/themes/ManageSiteAppearanceModule"}]
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["action"] == "ManageSiteThemeAction"
        assert save_body["event"] == "saveAppearance"

    def test_set_appearance_external_theme_sends_empty_string_theme_id(self, site_categories_single):
        site = _make_site(site_categories_single)
        SiteSettingsAccessor(site).set_appearance_external_theme("_default", "https://example.com/theme.css")
        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert '"theme_id": ""' in save_body["categories"] or '"theme_id":""' in save_body["categories"]


class TestGetGeneral:
    def test_reads_all_fields(self, site_general_form):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = site_general_form
        site.amc_request.return_value = [response]

        settings = SiteSettingsAccessor(site).get_general()

        assert settings.name == "My Site"
        assert settings.subtitle == "A subtitle"
        assert settings.language == "ja"
        assert settings.description == "A description"
        assert settings.default_page == "start"
        assert settings.welcome_page == "welcome"

    def test_missing_field_is_none_not_guessed(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok", "body": "<div></div>"}
        site.amc_request.return_value = [response]

        settings = SiteSettingsAccessor(site).get_general()

        assert settings.name is None
        assert settings.language is None


class TestSaveGeneralReadModifyWrite:
    def _mocked_site(self, get_payload: dict, save_payload: dict | None = None) -> MagicMock:
        site = MagicMock()
        get_response = MagicMock()
        get_response.json.return_value = get_payload
        save_response = MagicMock()
        save_response.json.return_value = save_payload or {"status": "ok"}
        site.amc_request.side_effect = [[get_response], [save_response]]
        return site

    def test_only_name_given_preserves_other_fields(self, site_general_form):
        site = self._mocked_site(site_general_form)

        SiteSettingsAccessor(site).save_general(name="New Title")

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["name"] == "New Title"
        assert save_body["subtitle"] == "A subtitle"
        assert save_body["language"] == "ja"
        assert save_body["description"] == "A description"
        assert save_body["default_page"] == "start"
        assert save_body["welcome_page"] == "welcome"

    def test_explicit_empty_string_clears_a_field(self, site_general_form):
        site = self._mocked_site(site_general_form)

        SiteSettingsAccessor(site).save_general(subtitle="")

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["subtitle"] == ""
        assert save_body["name"] == "My Site"

    def test_no_arguments_resends_all_current_values(self, site_general_form):
        site = self._mocked_site(site_general_form)

        SiteSettingsAccessor(site).save_general()

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["name"] == "My Site"
        assert save_body["subtitle"] == "A subtitle"
        assert save_body["language"] == "ja"
        assert save_body["description"] == "A description"
        assert save_body["default_page"] == "start"
        assert save_body["welcome_page"] == "welcome"

    def test_returns_new_unixname(self, site_general_form):
        site = self._mocked_site(site_general_form, {"status": "ok", "unixName": "new-name"})

        result = SiteSettingsAccessor(site).save_general(name="Test Site")

        assert result == "new-name"

    def test_returns_none_without_unixname_change(self, site_general_form):
        site = self._mocked_site(site_general_form)

        result = SiteSettingsAccessor(site).save_general(name="Test Site")

        assert result is None

    def test_empty_name_raises_form_errors(self, site_general_form):
        site = MagicMock()
        get_response = MagicMock()
        get_response.json.return_value = site_general_form
        site.amc_request.side_effect = [
            [get_response],
            FormErrorsException(
                "form_errors",
                "form_errors",
                {
                    "status": "form_errors",
                    "formErrors": {"name": "Please provide the site title"},
                    "message": "Form errors",
                },
            ),
        ]

        with pytest.raises(FormErrorsException) as exc_info:
            SiteSettingsAccessor(site).save_general(name="")

        assert exc_info.value.errors["name"] == "Please provide the site title"


class TestGetDomain:
    def test_reads_fields_by_id(self, site_domain_module):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = site_domain_module
        site.amc_request.return_value = [response]

        settings = SiteSettingsAccessor(site).get_domain()

        assert settings.domain == "example.com"
        assert settings.domain_default is True
        assert settings.redirects == ["a.com", "b.com"]


class TestSaveDomainReadModifyWrite:
    def test_too_many_redirects_raises_without_any_request(self):
        site = MagicMock()
        with pytest.raises(ValueError, match="10"):
            SiteSettingsAccessor(site).save_domain(redirects=[f"r{i}.com" for i in range(11)])
        site.amc_request.assert_not_called()

    def test_joins_redirects_with_semicolon(self, site_domain_module):
        site = MagicMock()
        get_response = MagicMock()
        get_response.json.return_value = site_domain_module
        save_response = MagicMock()
        save_response.json.return_value = {"status": "ok"}
        site.amc_request.side_effect = [[get_response], [save_response]]

        SiteSettingsAccessor(site).save_domain(redirects=["a.com", "b.com"])

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["redirects"] == "a.com;b.com"

    def test_only_domain_given_preserves_redirects_and_default_flag(self, site_domain_module):
        site = MagicMock()
        get_response = MagicMock()
        get_response.json.return_value = site_domain_module
        save_response = MagicMock()
        save_response.json.return_value = {"status": "ok"}
        site.amc_request.side_effect = [[get_response], [save_response]]

        SiteSettingsAccessor(site).save_domain(domain="new.example.com")

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["domain"] == "new.example.com"
        assert save_body["redirects"] == "a.com;b.com"
        assert save_body["domainDefault"] == "true"


class TestGetAccessPolicy:
    def test_reads_all_fields(self, site_access_policy_form):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = site_access_policy_form
        site.amc_request.return_value = [response]

        settings = SiteSettingsAccessor(site).get_access_policy()

        assert settings.privacy == "closed"
        assert settings.by_apply is True
        assert settings.by_domain == "example.com"
        assert settings.by_password is False
        assert settings.password == ""
        assert settings.allow_hotlink is True
        assert settings.landing_page == "start"
        assert settings.hide_nav is False


class TestSaveAccessPolicyReadModifyWrite:
    def _mocked_site(self, get_payload: dict) -> MagicMock:
        site = MagicMock()
        get_response = MagicMock()
        get_response.json.return_value = get_payload
        save_response = MagicMock()
        save_response.json.return_value = {"status": "ok"}
        site.amc_request.side_effect = [[get_response], [save_response]]
        return site

    def test_no_privacy_given_keeps_current_value(self, site_access_policy_form):
        site = self._mocked_site(site_access_policy_form)

        SiteSettingsAccessor(site).save_access_policy()

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["privacy"] == "closed"
        assert save_body["by_domain"] == "example.com"
        assert save_body["landingPage"] == "start"
        # by_apply / allowHotlink were checked in the fixture, so they must
        # still be sent even though this call didn't touch them
        assert save_body["by_apply"] == "on"
        assert save_body["allowHotlink"] == "on"
        assert "hideNav" not in save_body

    def test_privacy_cannot_be_determined_raises(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok", "body": "<form id='sm-private-form'></form>"}
        site.amc_request.return_value = [response]

        with pytest.raises(ValueError, match="privacy"):
            SiteSettingsAccessor(site).save_access_policy()

    def test_viewers_from_ids(self, site_access_policy_form):
        site = self._mocked_site(site_access_policy_form)

        SiteSettingsAccessor(site).save_access_policy(viewers=[111, 222])

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["viewers"] == "111,222"

    def test_viewers_omitted_when_not_given(self, site_access_policy_form):
        site = self._mocked_site(site_access_policy_form)

        SiteSettingsAccessor(site).save_access_policy()

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert "viewers" not in save_body

    def test_explicit_privacy_overrides_current_value(self, site_access_policy_form):
        site = self._mocked_site(site_access_policy_form)

        SiteSettingsAccessor(site).save_access_policy(privacy="private")

        save_body = site.amc_request.call_args_list[1][0][0][0]
        assert save_body["privacy"] == "private"


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
