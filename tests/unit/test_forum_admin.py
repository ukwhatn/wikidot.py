"""forum_adminモジュールのユニットテスト"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from wikidot.common.exceptions import ResponseDataException
from wikidot.module.forum_admin import (
    ForumCategoryPermissionOverride,
    ForumLayout,
    ForumLayoutCategory,
    ForumLayoutGroup,
    activate_forum,
    save_forum_permissions,
    set_forum_default_nesting,
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


class TestForumCategoryPermissionOverride:
    def test_to_dict_with_explicit_permissions(self) -> None:
        perms = ForumPermissions.decode("t:m;p:arm;e:m")
        override = ForumCategoryPermissionOverride(category_id=7001, permissions=perms)

        result = override.to_dict()

        assert result["category_id"] == 7001
        assert result["permissions"] == perms.encode()

    def test_to_dict_with_none_means_inherit_default(self) -> None:
        override = ForumCategoryPermissionOverride(category_id=7001, permissions=None)

        assert override.to_dict() == {"category_id": 7001, "permissions": None}


class TestSaveForumPermissions:
    def test_sends_default_and_category_overrides(self) -> None:
        site = _make_site()
        default_permissions = ForumPermissions.decode("t:m;p:arm;e:m")
        overrides = [ForumCategoryPermissionOverride(category_id=7001, permissions=None)]

        save_forum_permissions(site, default_permissions, overrides)

        body = site.amc_request.call_args[0][0][0]
        assert body["action"] == "ManageSiteForumAction"
        assert body["event"] == "saveForumPermissions"
        assert body["default_permissions"] == default_permissions.encode()
        assert body["categories"] == '[{"category_id": 7001, "permissions": null}]'

    def test_none_category_permissions_sends_empty_array(self) -> None:
        site = _make_site()
        default_permissions = ForumPermissions.decode("t:m;p:arm;e:m")

        save_forum_permissions(site, default_permissions, None)

        body = site.amc_request.call_args[0][0][0]
        assert body["categories"] == "[]"
