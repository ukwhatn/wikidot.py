"""SearchPagesQueryのユニットテスト"""

from wikidot.module.page import SearchPagesQuery


class TestSearchPagesQueryInit:
    """SearchPagesQueryの初期化テスト"""

    def test_default_values(self):
        """デフォルト値のテスト"""
        query = SearchPagesQuery()
        assert query.pagetype == "*"
        assert query.category == "*"
        assert query.tags is None
        assert query.parent is None
        assert query.link_to is None
        assert query.created_at is None
        assert query.updated_at is None
        assert query.created_by is None
        assert query.rating is None
        assert query.votes is None
        assert query.name is None
        assert query.fullname is None
        assert query.range is None
        assert query.order == "created_at desc"
        assert query.offset == 0
        assert query.limit is None
        assert query.perPage == 250
        assert query.separate == "no"
        assert query.wrapper == "no"

    def test_custom_values(self):
        """カスタム値のテスト"""
        query = SearchPagesQuery(
            pagetype="normal",
            category="scp",
            tags="tale",
            order="rating desc",
            limit=100,
        )
        assert query.pagetype == "normal"
        assert query.category == "scp"
        assert query.tags == "tale"
        assert query.order == "rating desc"
        assert query.limit == 100

    def test_tags_as_list(self):
        """タグをリストで指定するテスト"""
        query = SearchPagesQuery(tags=["scp", "safe", "humanoid"])
        assert query.tags == ["scp", "safe", "humanoid"]


class TestSearchPagesQueryAsDict:
    """SearchPagesQuery.as_dict()のテスト"""

    def test_basic_as_dict(self):
        """基本的なas_dictのテスト"""
        query = SearchPagesQuery()
        result = query.as_dict()
        # デフォルト値がNoneでないものが含まれる
        assert "pagetype" in result
        assert result["pagetype"] == "*"
        assert "category" in result
        assert result["category"] == "*"
        assert "order" in result
        assert result["order"] == "created_at desc"
        # Noneの値は含まれない
        assert "tags" not in result
        assert "parent" not in result
        assert "limit" not in result

    def test_as_dict_with_custom_values(self):
        """カスタム値でのas_dictのテスト"""
        query = SearchPagesQuery(
            category="scp",
            tags="keter",
            limit=50,
            offset=10,
        )
        result = query.as_dict()
        assert result["category"] == "scp"
        assert result["tags"] == "keter"
        assert result["limit"] == 50
        assert result["offset"] == 10

    def test_as_dict_tags_list_conversion(self):
        """タグリストが文字列に変換されるテスト"""
        query = SearchPagesQuery(tags=["scp", "euclid", "humanoid"])
        result = query.as_dict()
        assert result["tags"] == "scp euclid humanoid"

    def test_as_dict_tags_string_unchanged(self):
        """タグ文字列がそのまま保持されるテスト"""
        query = SearchPagesQuery(tags="scp euclid")
        result = query.as_dict()
        assert result["tags"] == "scp euclid"

    def test_as_dict_excludes_none_values(self):
        """None値が除外されるテスト"""
        query = SearchPagesQuery(
            category="test",
            tags=None,
            limit=None,
        )
        result = query.as_dict()
        assert "category" in result
        assert "tags" not in result
        assert "limit" not in result

    def test_as_dict_includes_zero_values(self):
        """0値が含まれるテスト"""
        query = SearchPagesQuery(offset=0)
        result = query.as_dict()
        assert "offset" in result
        assert result["offset"] == 0


class TestSearchPagesQueryUseCases:
    """SearchPagesQueryの実用的なユースケーステスト"""

    def test_scp_search_query(self):
        """SCP記事検索クエリのテスト"""
        query = SearchPagesQuery(
            category="scp",
            tags=["scp", "keter"],
            order="rating desc",
            limit=100,
        )
        result = query.as_dict()
        assert result["category"] == "scp"
        assert result["tags"] == "scp keter"
        assert result["order"] == "rating desc"
        assert result["limit"] == 100

    def test_paginated_search_query(self):
        """ページネーション付き検索クエリのテスト"""
        query = SearchPagesQuery(
            offset=100,
            limit=50,
            perPage=50,
        )
        result = query.as_dict()
        assert result["offset"] == 100
        assert result["limit"] == 50
        assert result["perPage"] == 50

    def test_date_filtered_search_query(self):
        """日付フィルタ付き検索クエリのテスト"""
        query = SearchPagesQuery(
            created_at=">=2020-01-01",
            updated_at="<=2023-12-31",
        )
        result = query.as_dict()
        assert result["created_at"] == ">=2020-01-01"
        assert result["updated_at"] == "<=2023-12-31"

    def test_rating_filtered_search_query(self):
        """評価フィルタ付き検索クエリのテスト"""
        query = SearchPagesQuery(
            rating=">=50",
            votes=">=10",
        )
        result = query.as_dict()
        assert result["rating"] == ">=50"
        assert result["votes"] == ">=10"

    def test_fullname_search_query(self):
        """フルネーム検索クエリのテスト"""
        query = SearchPagesQuery(
            fullname="scp-173",
        )
        result = query.as_dict()
        assert result["fullname"] == "scp-173"


class TestSearchPagesQueryValidation:
    """SearchPagesQueryのバリデーションテスト"""

    def test_invalid_parameter_raises_value_error(self):
        """無効なパラメータでValueErrorが発生すること"""
        import pytest

        with pytest.raises(ValueError, match="Invalid query parameters"):
            SearchPagesQuery(invalid_param="value")

    def test_multiple_invalid_parameters_raises_value_error(self):
        """複数の無効なパラメータでValueErrorが発生すること"""
        import pytest

        with pytest.raises(ValueError, match="Invalid query parameters"):
            SearchPagesQuery(invalid_param1="value1", invalid_param2="value2")

    def test_mixed_valid_invalid_parameters_raises_value_error(self):
        """有効なパラメータと無効なパラメータが混在する場合にValueErrorが発生すること"""
        import pytest

        with pytest.raises(ValueError, match="Invalid query parameters"):
            SearchPagesQuery(category="scp", invalid_param="value")

    def test_all_valid_parameters_work(self):
        """すべて有効なパラメータは正常に動作すること"""
        query = SearchPagesQuery(
            pagetype="normal",
            category="scp",
            tags="tale",
            parent="scp-001",
            link_to="scp-002",
            created_at=">=2020-01-01",
            updated_at="<=2023-12-31",
            created_by="test-user",
            rating=">=50",
            votes=">=10",
            name="test-page",
            fullname="scp-173",
            range="1-100",
            order="rating desc",
            offset=10,
            limit=50,
            perPage=100,
            separate="yes",
            wrapper="yes",
        )
        result = query.as_dict()
        assert result["category"] == "scp"
        assert result["tags"] == "tale"
