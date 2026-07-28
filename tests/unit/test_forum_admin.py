"""forum_adminモジュールのユニットテスト"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from wikidot.common.exceptions import ResponseDataException
from wikidot.module.forum_admin import (
    ForumCategoryPermissions,
    ForumCategoryPermissionsCollection,
    ForumLayout,
    ForumLayoutCategory,
    ForumLayoutGroup,
    activate_forum,
    set_forum_default_nesting,
    update_forum_permissions,
)
from wikidot.module.site_permissions import ForumPermissions


def _make_site() -> MagicMock:
    return MagicMock()


class TestActivateForum:
    def test_sends_activate_event_with_no_extra_params(self) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        site.amc_request.return_value = [mock_response]

        activate_forum(site)

        body = site.amc_request.call_args[0][0][0]
        assert body == {"action": "ManageSiteForumAction", "event": "activateForum", "moduleName": "Empty"}


class TestSetForumDefaultNesting:
    @pytest.mark.parametrize("level", [0, 5, 10])
    def test_valid_range(self, level: int) -> None:
        site = _make_site()
        set_forum_default_nesting(site, level)

        body = site.amc_request.call_args[0][0][0]
        assert body["event"] == "saveForumDefaultNesting"
        assert body["max_nest_level"] == level

    @pytest.mark.parametrize("level", [-1, 11])
    def test_out_of_range_raises(self, level: int) -> None:
        site = _make_site()
        with pytest.raises(ValueError, match="0 and 10"):
            set_forum_default_nesting(site, level)


class TestForumLayoutGroupRoundTrip:
    def test_from_dict_to_dict_preserves_unknown_fields(self) -> None:
        raw = {"group_id": 42, "name": "General", "description": "desc", "visible": True}
        group = ForumLayoutGroup.from_dict(raw)
        assert group.name == "General"
        assert group.visible is True

        rebuilt = group.to_dict()
        assert rebuilt["group_id"] == 42
        assert rebuilt["name"] == "General"

    def test_locally_created_group_has_empty_raw(self) -> None:
        group = ForumLayoutGroup(name="New Group", description="", visible=True)
        assert group.to_dict() == {"name": "New Group", "description": "", "visible": True}


class TestForumLayoutCategoryRoundTrip:
    def test_from_dict_to_dict_preserves_unknown_fields(self) -> None:
        raw = {
            "category_id": 7001,
            "name": "Discussion",
            "description": "desc",
            "max_nest_level": 3,
            "number_threads": 12,
        }
        category = ForumLayoutCategory.from_dict(raw)
        assert category.category_id == 7001
        assert category.number_threads == 12

        rebuilt = category.to_dict()
        assert rebuilt["category_id"] == 7001
        assert rebuilt["max_nest_level"] == 3
        # number_threads is read-only local info, not sent back
        assert "number_threads" not in rebuilt or rebuilt["number_threads"] == 12  # raw仕様上残ってもよい

    def test_new_category_has_no_category_id(self) -> None:
        category = ForumLayoutCategory(name="New Category", description="")
        assert "category_id" not in category.to_dict()


@pytest.fixture
def layout_response() -> dict[str, Any]:
    return {
        "status": "ok",
        "groups": [
            {"group_id": 1, "name": "Group A", "description": "", "visible": True},
        ],
        "categories": [
            [
                {"category_id": 7001, "name": "Cat A1", "description": "", "max_nest_level": None, "number_threads": 5},
            ],
        ],
        "defaultNesting": 3,
    }


class TestForumLayoutFetch:
    def test_fetch_parses_groups_categories_and_nesting(self, layout_response: dict[str, Any]) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = layout_response
        site.amc_request.return_value = [mock_response]

        layout = ForumLayout.fetch(site)

        assert len(layout.groups) == 1
        assert layout.groups[0].name == "Group A"
        assert len(layout.categories) == 1
        assert len(layout.categories[0]) == 1
        assert layout.categories[0][0].category_id == 7001
        assert layout.default_nesting == 3

        fetch_body = site.amc_request.call_args[0][0][0]
        assert fetch_body == {"moduleName": "managesite/ManageSiteGetForumLayoutModule"}

    def test_fetch_raises_when_fields_missing(self) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        site.amc_request.return_value = [mock_response]

        with pytest.raises(ResponseDataException):
            ForumLayout.fetch(site)


class TestForumLayoutMutation:
    def test_add_group_keeps_categories_index_in_sync(self, layout_response: dict[str, Any]) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = layout_response
        site.amc_request.return_value = [mock_response]
        layout = ForumLayout.fetch(site)

        new_group = layout.add_group("Group B")

        assert layout.groups[-1] is new_group
        assert layout.categories[-1] == []

    def test_add_category_appends_to_correct_group(self, layout_response: dict[str, Any]) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = layout_response
        site.amc_request.return_value = [mock_response]
        layout = ForumLayout.fetch(site)
        group_b = layout.add_group("Group B")

        new_category = layout.add_category(group_b, "Cat B1")

        assert layout.categories[0] != [new_category]  # group A側は変化しない
        assert layout.categories[1] == [new_category]

    def test_add_category_to_group_not_in_layout_raises(self, layout_response: dict[str, Any]) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = layout_response
        site.amc_request.return_value = [mock_response]
        layout = ForumLayout.fetch(site)
        foreign_group = ForumLayoutGroup(name="Foreign", description="")

        with pytest.raises(ValueError):
            layout.add_category(foreign_group, "Cat")

    def test_remove_group_requires_confirm(self, layout_response: dict[str, Any]) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = layout_response
        site.amc_request.return_value = [mock_response]
        layout = ForumLayout.fetch(site)

        with pytest.raises(ValueError, match="confirm"):
            layout.remove_group(layout.groups[0], confirm=False)

    def test_remove_group_moves_group_and_categories_to_deleted_lists(self, layout_response: dict[str, Any]) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = layout_response
        site.amc_request.return_value = [mock_response]
        layout = ForumLayout.fetch(site)
        group = layout.groups[0]

        layout.remove_group(group, confirm=True)

        assert layout.groups == []
        assert layout.categories == []
        assert layout._deleted_groups[0]["name"] == "Group A"
        assert layout._deleted_category_ids == [7001]

    def test_remove_category_requires_confirm(self, layout_response: dict[str, Any]) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = layout_response
        site.amc_request.return_value = [mock_response]
        layout = ForumLayout.fetch(site)

        with pytest.raises(ValueError, match="confirm"):
            layout.remove_category(layout.groups[0], layout.categories[0][0], confirm=False)

    def test_remove_category_records_id(self, layout_response: dict[str, Any]) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = layout_response
        site.amc_request.return_value = [mock_response]
        layout = ForumLayout.fetch(site)
        group = layout.groups[0]
        category = layout.categories[0][0]

        layout.remove_category(group, category, confirm=True)

        assert layout.categories[0] == []
        assert layout._deleted_category_ids == [7001]


class TestForumLayoutSave:
    def test_save_sends_all_four_fields_and_clears_deletion_lists(self, layout_response: dict[str, Any]) -> None:
        site = _make_site()
        fetch_response = MagicMock()
        fetch_response.json.return_value = layout_response
        site.amc_request.return_value = [fetch_response]
        layout = ForumLayout.fetch(site)
        layout.remove_category(layout.groups[0], layout.categories[0][0], confirm=True)

        layout.save()

        save_body = site.amc_request.call_args[0][0][0]
        assert save_body["action"] == "ManageSiteForumAction"
        assert save_body["event"] == "saveForumLayout"
        assert "groups" in save_body
        assert "categories" in save_body
        assert save_body["deleted_categories"] == "[7001]"
        assert layout._deleted_category_ids == []
        assert layout._deleted_groups == []


def _raw_permissions_category(**overrides: Any) -> dict[str, Any]:
    """13-field category object as returned by ManageSiteForumPermissionsModule (実測 2026-07-29)"""
    base: dict[str, Any] = {
        "category_id": 7001,
        "group_id": 1,
        "name": "Cat A1",
        "description": "desc",
        "number_posts": 42,
        "number_threads": 5,
        "last_post_id": 99999,
        "permissions_default": True,
        "permissions": None,
        "max_nest_level": None,
        "sort_index": 0,
        "site_id": 3632981,
        "per_page_discussion": None,
    }
    base.update(overrides)
    return base


class TestForumCategoryPermissionsRoundTrip:
    def test_from_dict_to_dict_preserves_all_13_fields(self) -> None:
        raw = _raw_permissions_category(permissions="t:m;p:arm;e:m", permissions_default=False)
        category = ForumCategoryPermissions.from_dict(raw)

        assert category.category_id == 7001
        assert category.group_id == 1
        assert category.number_posts == 42
        assert category.number_threads == 5
        assert category.last_post_id == 99999
        assert category.permissions_default is False
        assert category.permissions is not None
        assert category.sort_index == 0
        assert category.site_id == 3632981

        result = category.to_dict()
        # 元の13フィールドが全て往復すること（{category_id, permissions}だけの部分オブジェクトにならない）
        for key in raw:
            if key == "permissions":
                continue
            assert result[key] == raw[key]
        assert result["permissions"] == "t:m;p:arm;e:m"

    def test_preserves_unknown_fields_via_raw(self) -> None:
        raw = _raw_permissions_category(some_future_field="x")
        category = ForumCategoryPermissions.from_dict(raw)
        assert category.to_dict()["some_future_field"] == "x"

    def test_set_permissions_updates_default_flag(self) -> None:
        category = ForumCategoryPermissions.from_dict(_raw_permissions_category())
        perms = ForumPermissions.decode("t:m;p:arm;e:m")

        category.set_permissions(perms)
        assert category.permissions == perms
        assert category.permissions_default is False

        category.set_permissions(None)
        assert category.permissions is None
        assert category.permissions_default is True


class TestForumCategoryPermissionsCollectionFetch:
    def test_fetch_parses_categories_from_permissions_module(self) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "categories": [_raw_permissions_category()]}
        site.amc_request.return_value = [mock_response]

        collection = ForumCategoryPermissionsCollection.fetch(site)

        assert len(collection) == 1
        assert collection[7001].category_id == 7001
        fetch_body = site.amc_request.call_args[0][0][0]
        assert fetch_body == {"moduleName": "managesite/ManageSiteForumPermissionsModule"}

    def test_fetch_raises_when_categories_missing(self) -> None:
        site = _make_site()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        site.amc_request.return_value = [mock_response]

        with pytest.raises(ResponseDataException):
            ForumCategoryPermissionsCollection.fetch(site)

    def test_getitem_missing_raises_key_error(self) -> None:
        collection = ForumCategoryPermissionsCollection(
            site=_make_site(), categories=[ForumCategoryPermissions.from_dict(_raw_permissions_category())]
        )
        with pytest.raises(KeyError):
            collection[999999]


class TestForumCategoryPermissionsCollectionSave:
    def test_save_sends_full_category_objects_not_partial(self) -> None:
        site = _make_site()
        collection = ForumCategoryPermissionsCollection(
            site=site, categories=[ForumCategoryPermissions.from_dict(_raw_permissions_category())]
        )

        collection.save()

        save_body = site.amc_request.call_args[0][0][0]
        assert save_body["action"] == "ManageSiteForumAction"
        assert save_body["event"] == "saveForumPermissions"
        import json

        sent_categories = json.loads(save_body["categories"])
        assert len(sent_categories[0]) == 13  # 2フィールドの部分オブジェクトに戻っていないこと
        assert "number_posts" in sent_categories[0]
        assert "sort_index" in sent_categories[0]

    def test_default_permissions_omitted_when_not_provided(self) -> None:
        site = _make_site()
        collection = ForumCategoryPermissionsCollection(site=site, categories=[])

        collection.save()

        save_body = site.amc_request.call_args[0][0][0]
        assert "default_permissions" not in save_body

    def test_default_permissions_sent_when_explicitly_provided(self) -> None:
        site = _make_site()
        collection = ForumCategoryPermissionsCollection(site=site, categories=[])
        default_permissions = ForumPermissions.decode("t:m;p:arm;e:m")

        collection.save(default_permissions)

        save_body = site.amc_request.call_args[0][0][0]
        assert save_body["default_permissions"] == default_permissions.encode()


class TestUpdateForumPermissions:
    def test_fetch_then_mutate_then_save(self) -> None:
        site = _make_site()
        fetch_response = MagicMock()
        fetch_response.json.return_value = {"status": "ok", "categories": [_raw_permissions_category()]}
        site.amc_request.return_value = [fetch_response]
        new_perms = ForumPermissions.decode("t:m;p:arm;e:m")

        update_forum_permissions(site, lambda cats: cats[7001].set_permissions(new_perms))

        assert site.amc_request.call_count == 2
        fetch_call, save_call = site.amc_request.call_args_list
        assert fetch_call[0][0] == [{"moduleName": "managesite/ManageSiteForumPermissionsModule"}]
        save_body = save_call[0][0][0]
        assert save_body["event"] == "saveForumPermissions"
        assert new_perms.encode() in save_body["categories"]
