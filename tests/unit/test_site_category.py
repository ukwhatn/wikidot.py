"""site_categoryモジュールのユニットテスト"""

from unittest.mock import MagicMock

import pytest

from wikidot.common.exceptions import ResponseDataException
from wikidot.module.site_category import SiteCategory, SiteCategoryCollection, SiteLicense
from wikidot.module.site_permissions import PagePermissions, RatingSettings


class TestSiteCategoryRoundTrip:
    """SiteCategory.from_dict -> to_dict のラウンドトリップ"""

    def test_roundtrip_matches_original(self, site_categories_single):
        raw = site_categories_single["categories"][0]
        category = SiteCategory.from_dict(raw)

        assert category.to_dict() == raw

    def test_decoded_fields(self, site_categories_single):
        raw = site_categories_single["categories"][0]
        category = SiteCategory.from_dict(raw)

        assert category.category_id == 30228632
        assert category.name == "_default"
        assert isinstance(category.permissions, PagePermissions)
        assert category.permissions.view == {"anonymous", "registered", "member", "author"}
        assert isinstance(category.rating, RatingSettings)
        assert category.rating.kind == "plus_minus"

    def test_unknown_field_survives_roundtrip(self, site_categories_single):
        # A field this library does not model must not be dropped when
        # rebuilding the dict for the save request (see 30_plan.md D3)
        raw = dict(site_categories_single["categories"][0])
        raw["some_future_field"] = "unmodeled_value"

        category = SiteCategory.from_dict(raw)

        assert category.to_dict()["some_future_field"] == "unmodeled_value"

    def test_permissions_default_true_means_none(self, site_categories_single):
        raw = dict(site_categories_single["categories"][0])
        raw["permissions_default"] = True
        raw["permissions"] = None

        category = SiteCategory.from_dict(raw)

        assert category.permissions is None
        assert category.to_dict()["permissions"] is None

    def test_set_permissions_updates_single_field_and_clears_default(self, site_categories_single):
        raw = site_categories_single["categories"][0]
        category = SiteCategory.from_dict(raw)

        category.set_permissions(view={"anonymous", "registered", "member", "author"})

        assert category.permissions_default is False
        # untouched fields keep their decoded value
        assert category.permissions.create == {"member"}


class TestSiteCategoryCollection:
    def test_getitem_found(self, site_categories_single):
        site = MagicMock()
        categories = [SiteCategory.from_dict(c) for c in site_categories_single["categories"]]
        collection = SiteCategoryCollection(site=site, categories=categories)

        assert collection["_default"].category_id == 30228632

    def test_getitem_not_found_raises(self, site_categories_single):
        site = MagicMock()
        categories = [SiteCategory.from_dict(c) for c in site_categories_single["categories"]]
        collection = SiteCategoryCollection(site=site, categories=categories)

        with pytest.raises(KeyError):
            collection["nonexistent"]

    def test_len_and_names(self, site_categories_single):
        site = MagicMock()
        categories = [SiteCategory.from_dict(c) for c in site_categories_single["categories"]]
        collection = SiteCategoryCollection(site=site, categories=categories)

        assert len(collection) == 1
        assert collection.names() == ["_default"]

    def test_fetch_parses_categories(self, site_categories_single):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = site_categories_single
        site.amc_request.return_value = [response]

        collection = SiteCategoryCollection.fetch(site, "managesite/ManageSitePermissionsModule")

        assert len(collection) == 1
        site.amc_request.assert_called_once_with([{"moduleName": "managesite/ManageSitePermissionsModule"}])

    def test_fetch_missing_categories_raises(self):
        site = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok", "body": ""}
        site.amc_request.return_value = [response]

        with pytest.raises(ResponseDataException):
            SiteCategoryCollection.fetch(site, "managesite/ManageSitePermissionsModule")

    def test_save_sends_full_array_as_json(self, site_categories_single):
        site = MagicMock()
        categories = [SiteCategory.from_dict(c) for c in site_categories_single["categories"]]
        collection = SiteCategoryCollection(site=site, categories=categories)

        collection.save("ManageSiteAction", "savePermissions")

        body = site.amc_request.call_args[0][0][0]
        assert body["action"] == "ManageSiteAction"
        assert body["event"] == "savePermissions"
        assert body["moduleName"] == "Empty"
        assert isinstance(body["categories"], str)
        assert "_default" in body["categories"]


class TestSiteLicense:
    def test_other_is_one(self):
        assert SiteLicense.OTHER.value == 1

    def test_all_15_values_present(self):
        assert len(SiteLicense) == 15
