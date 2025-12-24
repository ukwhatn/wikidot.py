"""統合テスト用フィクスチャ"""

from __future__ import annotations

import os
import random
import string
import time
from collections.abc import Callable, Generator

import pytest

# 統合テストは環境変数が設定されている場合のみ実行
WIKIDOT_USERNAME = os.environ.get("WIKIDOT_USERNAME")
WIKIDOT_PASSWORD = os.environ.get("WIKIDOT_PASSWORD")
TEST_SITE_UNIX_NAME = "ukwhatn-ci"

# 認証情報が未設定の場合はスキップ
pytestmark = pytest.mark.skipif(
    not WIKIDOT_USERNAME or not WIKIDOT_PASSWORD,
    reason="WIKIDOT_USERNAME and WIKIDOT_PASSWORD environment variables are required",
)


def generate_page_name(prefix: str = "test") -> str:
    """テスト用ランダムページ名を生成

    フォーマット: {prefix}-{timestamp}-{random6chars}
    例: test-1703404800-abc123
    """
    timestamp = int(time.time())
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}-{timestamp}-{random_suffix}"


@pytest.fixture(scope="session")
def credentials() -> dict[str, str]:
    """テスト用認証情報"""
    assert WIKIDOT_USERNAME is not None
    assert WIKIDOT_PASSWORD is not None
    return {
        "username": WIKIDOT_USERNAME,
        "password": WIKIDOT_PASSWORD,
    }


@pytest.fixture(scope="session")
def client(credentials: dict[str, str]):
    """認証済みクライアント（セッション全体で共有）"""
    from wikidot import Client

    _client = Client(
        username=credentials["username"],
        password=credentials["password"],
    )
    yield _client
    # セッション終了時にクリーンアップ


@pytest.fixture(scope="session")
def site(client):
    """テストサイト（セッション全体で共有）"""
    return client.site.get(TEST_SITE_UNIX_NAME)


@pytest.fixture
def page_name_generator() -> Callable[[str], str]:
    """ページ名生成ヘルパー"""
    return generate_page_name


@pytest.fixture
def cleanup_pages(site) -> Generator[list[str], None, None]:
    """テスト終了時にページをクリーンアップ

    使用方法:
        def test_something(site, cleanup_pages):
            page_name = "test-page"
            cleanup_pages.append(page_name)
            # ... ページ作成
    """
    pages_to_cleanup: list[str] = []
    yield pages_to_cleanup

    for fullname in pages_to_cleanup:
        try:
            page = site.page.get(fullname, raise_when_not_found=False)
            if page is not None:
                page.destroy()
        except Exception as e:
            print(f"Warning: Failed to cleanup page {fullname}: {e}")
