"""pytest設定とフィクスチャ"""

import pytest


@pytest.fixture
def mock_credentials():
    """テスト用認証情報"""
    return {
        "username": "test_user",
        "password": "test_password",
    }
