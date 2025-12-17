"""pytest設定とフィクスチャ"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from wikidot.connector.ajax import AjaxModuleConnectorConfig
    from wikidot.module.site import Site

FIXTURES_DIR = Path(__file__).parent / "fixtures"
HTML_SAMPLES_DIR = FIXTURES_DIR / "html_samples"
AMC_RESPONSES_DIR = FIXTURES_DIR / "amc_responses"


# ============================================================
# 基本フィクスチャ
# ============================================================


@pytest.fixture
def mock_credentials() -> dict[str, str]:
    """テスト用認証情報"""
    return {
        "username": "test_user",
        "password": "test_password",
    }


# ============================================================
# クライアント関連フィクスチャ
# ============================================================


@pytest.fixture
def mock_amc_config() -> AjaxModuleConnectorConfig:
    """テスト用AMC設定（短いタイムアウト）"""
    from wikidot.connector.ajax import AjaxModuleConnectorConfig

    return AjaxModuleConnectorConfig(
        request_timeout=5,
        attempt_limit=2,
        retry_interval=0,
        semaphore_limit=5,
    )


@pytest.fixture
def mock_client_no_http() -> MagicMock:
    """HTTPリクエストなしでClientをモック"""
    from wikidot.connector.ajax import AjaxModuleConnectorConfig, AjaxRequestHeader

    mock = MagicMock()
    mock.amc_client = MagicMock()
    mock.amc_client.header = AjaxRequestHeader()
    mock.amc_client.config = AjaxModuleConnectorConfig(
        request_timeout=5,
        attempt_limit=2,
        retry_interval=0,
    )
    mock.is_logged_in = False
    return mock


@pytest.fixture
def mock_site_no_http(mock_client_no_http: MagicMock) -> Site:
    """HTTPリクエストなしでSiteを作成"""
    from wikidot.module.site import Site

    return Site(
        client=mock_client_no_http,
        id=123456,
        title="Test Site",
        unix_name="test-site",
        domain="test-site.wikidot.com",
        ssl_supported=True,
    )


# ============================================================
# AMCレスポンスフィクスチャ
# ============================================================


@pytest.fixture
def amc_ok_response() -> dict[str, Any]:
    """成功AMCレスポンス"""
    return {"status": "ok", "body": ""}


@pytest.fixture
def amc_error_response() -> Callable[[str, str], dict[str, Any]]:
    """エラーAMCレスポンスファクトリ"""

    def _make_error(status: str, message: str = "") -> dict[str, Any]:
        return {"status": status, "message": message}

    return _make_error


@pytest.fixture
def amc_try_again_response() -> dict[str, str]:
    """try_again AMCレスポンス"""
    return {"status": "try_again"}


@pytest.fixture
def amc_no_permission_response() -> dict[str, str]:
    """no_permission AMCレスポンス"""
    return {"status": "no_permission"}


# ============================================================
# ファイル読み込みヘルパー
# ============================================================


def _load_html(filename: str) -> str:
    """HTMLフィクスチャファイルを読み込む（内部用）"""
    path = HTML_SAMPLES_DIR / filename
    return path.read_text(encoding="utf-8").strip()


def _load_json(subdir: str, filename: str) -> dict[str, Any]:
    """JSONフィクスチャファイルを読み込む（内部用）"""
    path = AMC_RESPONSES_DIR / subdir / filename
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def load_html_fixture() -> Callable[[str], str]:
    """HTMLフィクスチャファイルを読み込む"""
    return _load_html


@pytest.fixture
def load_json_fixture() -> Callable[[str, str], dict[str, Any]]:
    """JSONフィクスチャファイルを読み込む"""

    def _load(subdir: str, filename: str) -> dict[str, Any]:
        return _load_json(subdir, filename)

    return _load


# ============================================================
# Printuser HTMLフィクスチャ
# ============================================================


@pytest.fixture
def printuser_regular_html() -> str:
    """通常ユーザーのprintuser HTML"""
    return _load_html("printuser_regular.html")


@pytest.fixture
def printuser_deleted_html() -> str:
    """削除済みユーザーのprintuser HTML"""
    return _load_html("printuser_deleted.html")


@pytest.fixture
def printuser_deleted_no_id_html() -> str:
    """ID無し削除済みユーザーのprintuser HTML"""
    return _load_html("printuser_deleted_no_id.html")


@pytest.fixture
def printuser_anonymous_html() -> str:
    """匿名ユーザーのprintuser HTML"""
    return _load_html("printuser_anonymous.html")


@pytest.fixture
def printuser_anonymous_no_ip_html() -> str:
    """IP無し匿名ユーザーのprintuser HTML"""
    return _load_html("printuser_anonymous_no_ip.html")


@pytest.fixture
def printuser_guest_html() -> str:
    """ゲストユーザーのprintuser HTML"""
    return _load_html("printuser_guest.html")


@pytest.fixture
def printuser_wikidot_html() -> str:
    """Wikidotシステムユーザーのprintuser HTML"""
    return _load_html("printuser_wikidot.html")


# ============================================================
# Odate HTMLフィクスチャ
# ============================================================


@pytest.fixture
def odate_html_factory() -> Callable[[int], str]:
    """odate HTML要素ファクトリ"""

    def _make_odate(unix_timestamp: int) -> str:
        return f'<span class="odate time_{unix_timestamp} format_%25e%20%25b%20%25Y%2C%20%25H%3A%25M%7Cagohover" style="cursor: help; display: inline;">17 Dec 2025, 12:00</span>'

    return _make_odate


@pytest.fixture
def odate_html_no_time() -> str:
    """time_クラスなしのodate HTML"""
    return _load_html("odate_no_time.html")


@pytest.fixture
def odate_html_multiple_classes() -> str:
    """複数クラス付きodate HTML"""
    return _load_html("odate_multiple_classes.html")


# ============================================================
# サイトHTMLフィクスチャ
# ============================================================


@pytest.fixture
def site_html_response() -> str:
    """サイトホームページHTML"""
    return _load_html("site_homepage.html")


@pytest.fixture
def user_profile_html() -> str:
    """ユーザープロファイルHTML"""
    return _load_html("user_profile.html")


@pytest.fixture
def user_profile_not_found_html() -> str:
    """存在しないユーザーのプロファイルHTML"""
    return _load_html("user_profile_notfound.html")
