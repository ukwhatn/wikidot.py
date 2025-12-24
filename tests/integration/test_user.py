"""ユーザー検索の統合テスト"""

from __future__ import annotations


class TestUserSearch:
    """ユーザー検索テスト"""

    def test_1_get_user_by_name(self, client):
        """1. ユーザー名でユーザー取得"""
        # 既知のユーザー名で取得
        user = client.user.get("ukwhatn")
        assert user is not None
        assert user.name.lower() == "ukwhatn"

    def test_2_get_nonexistent_user(self, client):
        """2. 存在しないユーザー取得"""
        user = client.user.get("nonexistent-user-12345678")
        assert user is None

    def test_3_user_properties(self, client):
        """3. ユーザープロパティ確認"""
        user = client.user.get("ukwhatn")
        assert user is not None
        assert user.id is not None
        assert user.name is not None
        assert user.unix_name is not None

    def test_4_get_bulk_users(self, client):
        """4. 複数ユーザー一括取得"""
        users = client.user.get_bulk(["ukwhatn"])
        assert users is not None
        assert len(users) >= 1
