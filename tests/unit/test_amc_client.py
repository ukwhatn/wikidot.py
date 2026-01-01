"""AMCクライアントのユニットテスト"""

import pytest
from pytest_httpx import HTTPXMock

from wikidot.common.exceptions import (
    AMCHttpStatusCodeException,
    ForbiddenException,
    NotFoundException,
    ResponseDataException,
    WikidotStatusCodeException,
)
from wikidot.connector.ajax import (
    AjaxModuleConnectorClient,
    AjaxModuleConnectorConfig,
    AjaxRequestHeader,
)


class TestAjaxRequestHeader:
    """AjaxRequestHeaderのテスト"""

    def test_default_values(self) -> None:
        """デフォルト値が正しく設定される"""
        header = AjaxRequestHeader()

        assert header.content_type == "application/x-www-form-urlencoded; charset=UTF-8"
        assert header.user_agent == "WikidotPy"
        assert header.referer == "https://www.wikidot.com/"
        assert header.cookie == {"wikidot_token7": 123456}

    def test_custom_values(self) -> None:
        """カスタム値が正しく設定される"""
        header = AjaxRequestHeader(
            content_type="text/plain",
            user_agent="CustomAgent",
            referer="https://example.com/",
            cookie={"session": "abc123"},
        )

        assert header.content_type == "text/plain"
        assert header.user_agent == "CustomAgent"
        assert header.referer == "https://example.com/"
        assert "session" in header.cookie
        assert "wikidot_token7" in header.cookie

    def test_set_cookie(self) -> None:
        """Cookieを追加できる"""
        header = AjaxRequestHeader()
        header.set_cookie("new_cookie", "value")

        assert header.cookie["new_cookie"] == "value"

    def test_delete_cookie(self) -> None:
        """Cookieを削除できる"""
        header = AjaxRequestHeader(cookie={"to_delete": "value"})
        header.delete_cookie("to_delete")

        assert "to_delete" not in header.cookie

    def test_get_header(self) -> None:
        """HTTPヘッダ辞書を取得できる"""
        header = AjaxRequestHeader()
        result = header.get_header()

        assert "Content-Type" in result
        assert "User-Agent" in result
        assert "Referer" in result
        assert "Cookie" in result
        assert "wikidot_token7=123456" in result["Cookie"]


class TestAjaxModuleConnectorConfig:
    """AjaxModuleConnectorConfigのテスト"""

    def test_default_values(self) -> None:
        """デフォルト値が正しく設定される"""
        config = AjaxModuleConnectorConfig()

        assert config.request_timeout == 20
        assert config.attempt_limit == 5
        assert config.retry_interval == 1.0
        assert config.max_backoff == 60.0
        assert config.backoff_factor == 2.0
        assert config.semaphore_limit == 10

    def test_custom_values(self) -> None:
        """カスタム値が正しく設定される"""
        config = AjaxModuleConnectorConfig(
            request_timeout=30,
            attempt_limit=5,
            retry_interval=2.0,
            max_backoff=120.0,
            backoff_factor=3.0,
            semaphore_limit=20,
        )

        assert config.request_timeout == 30
        assert config.attempt_limit == 5
        assert config.retry_interval == 2.0
        assert config.max_backoff == 120.0
        assert config.backoff_factor == 3.0
        assert config.semaphore_limit == 20


class TestAjaxModuleConnectorClientInit:
    """AjaxModuleConnectorClient初期化のテスト"""

    def test_www_is_always_ssl(self, httpx_mock: HTTPXMock) -> None:
        """wwwサイトは常にSSL対応"""
        client = AjaxModuleConnectorClient(site_name="www")

        assert client.ssl_supported is True
        assert client.site_name == "www"

    def test_site_with_ssl_redirect(self, httpx_mock: HTTPXMock) -> None:
        """HTTPSリダイレクトがあるサイトはSSL対応"""
        httpx_mock.add_response(
            url="http://test-site.wikidot.com",
            status_code=301,
            headers={"Location": "https://test-site.wikidot.com"},
        )

        client = AjaxModuleConnectorClient(site_name="test-site")

        assert client.ssl_supported is True

    def test_site_without_ssl(self, httpx_mock: HTTPXMock) -> None:
        """HTTPSリダイレクトがないサイトはSSL非対応"""
        httpx_mock.add_response(
            url="http://test-site.wikidot.com",
            status_code=200,
        )

        client = AjaxModuleConnectorClient(site_name="test-site")

        assert client.ssl_supported is False

    def test_site_not_found(self, httpx_mock: HTTPXMock) -> None:
        """存在しないサイトはNotFoundException"""
        httpx_mock.add_response(
            url="http://nonexistent.wikidot.com",
            status_code=404,
        )

        with pytest.raises(NotFoundException):
            AjaxModuleConnectorClient(site_name="nonexistent")


class TestAjaxModuleConnectorClientRequest:
    """AjaxModuleConnectorClient.requestのテスト"""

    def test_successful_request(self, httpx_mock: HTTPXMock) -> None:
        """成功するAMCリクエスト"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": "<div>test</div>", "CURRENT_TIMESTAMP": 1234567890},
        )

        client = AjaxModuleConnectorClient(site_name="www")
        responses = client.request([{"moduleName": "TestModule"}])

        assert len(responses) == 1
        assert responses[0].json()["status"] == "ok"

    def test_multiple_requests(self, httpx_mock: HTTPXMock) -> None:
        """複数リクエストを並行処理"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": "1"},
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": "2"},
        )

        client = AjaxModuleConnectorClient(site_name="www")
        responses = client.request(
            [
                {"moduleName": "Module1"},
                {"moduleName": "Module2"},
            ]
        )

        assert len(responses) == 2

    def test_retry_on_try_again(self, httpx_mock: HTTPXMock) -> None:
        """try_againでリトライ"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "try_again"},
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        config = AjaxModuleConnectorConfig(retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)
        responses = client.request([{"moduleName": "Test"}])

        assert len(httpx_mock.get_requests()) == 2
        assert responses[0].json()["status"] == "ok"

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    def test_max_retry_exceeded(self, httpx_mock: HTTPXMock) -> None:
        """リトライ上限超過でWikidotStatusCodeException"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "try_again"},
        )

        config = AjaxModuleConnectorConfig(attempt_limit=2, retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)

        with pytest.raises(WikidotStatusCodeException):
            client.request([{"moduleName": "Test"}])

    def test_no_permission_error(self, httpx_mock: HTTPXMock) -> None:
        """no_permissionでForbiddenException"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "no_permission"},
        )

        client = AjaxModuleConnectorClient(site_name="www")

        with pytest.raises(ForbiddenException):
            client.request([{"moduleName": "RestrictedModule"}])

    def test_other_error_status(self, httpx_mock: HTTPXMock) -> None:
        """その他のエラーステータスでWikidotStatusCodeException"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "some_error", "message": "Something went wrong"},
        )

        client = AjaxModuleConnectorClient(site_name="www")

        with pytest.raises(WikidotStatusCodeException):
            client.request([{"moduleName": "Test"}])

    def test_http_error_retry(self, httpx_mock: HTTPXMock) -> None:
        """HTTPエラーでリトライ"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            status_code=500,
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        config = AjaxModuleConnectorConfig(retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)
        client.request([{"moduleName": "Test"}])

        assert len(httpx_mock.get_requests()) == 2

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    def test_http_error_max_retry(self, httpx_mock: HTTPXMock) -> None:
        """HTTPエラーでリトライ上限超過"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            status_code=500,
        )

        config = AjaxModuleConnectorConfig(attempt_limit=2, retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)

        with pytest.raises(AMCHttpStatusCodeException):
            client.request([{"moduleName": "Test"}])

    def test_retry_on_non_json_response(self, httpx_mock: HTTPXMock) -> None:
        """非JSONレスポンスでリトライ"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            text="",  # 空レスポンス（JSONパースエラー）
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        config = AjaxModuleConnectorConfig(retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)
        responses = client.request([{"moduleName": "Test"}])

        assert len(httpx_mock.get_requests()) == 2
        assert responses[0].json()["status"] == "ok"

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    def test_non_json_response_max_retry(self, httpx_mock: HTTPXMock) -> None:
        """非JSONレスポンスでリトライ上限超過"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            text="not a json",
        )

        config = AjaxModuleConnectorConfig(attempt_limit=2, retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)

        with pytest.raises(ResponseDataException):
            client.request([{"moduleName": "Test"}])

    def test_retry_on_empty_json_response(self, httpx_mock: HTTPXMock) -> None:
        """空JSONレスポンスでリトライ"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={},  # 空オブジェクト
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        config = AjaxModuleConnectorConfig(retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)
        responses = client.request([{"moduleName": "Test"}])

        assert len(httpx_mock.get_requests()) == 2
        assert responses[0].json()["status"] == "ok"

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    def test_empty_response_max_retry(self, httpx_mock: HTTPXMock) -> None:
        """空レスポンスでリトライ上限超過"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={},
        )

        config = AjaxModuleConnectorConfig(attempt_limit=2, retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)

        with pytest.raises(ResponseDataException):
            client.request([{"moduleName": "Test"}])

    def test_return_exceptions_mode(self, httpx_mock: HTTPXMock) -> None:
        """return_exceptions=Trueで例外を返す"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "some_error"},
        )

        client = AjaxModuleConnectorClient(site_name="www")
        responses = client.request(
            [{"moduleName": "Good"}, {"moduleName": "Bad"}],
            return_exceptions=True,
        )

        assert len(responses) == 2
        # 順序は保証されないため、型でチェック
        types = [type(r).__name__ for r in responses]
        assert "Response" in types
        assert "WikidotStatusCodeException" in types

    def test_custom_site_name(self, httpx_mock: HTTPXMock) -> None:
        """サイト名を指定してリクエスト"""
        httpx_mock.add_response(
            url="http://other-site.wikidot.com",
            status_code=200,
        )
        httpx_mock.add_response(
            url="http://other-site.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        client = AjaxModuleConnectorClient(site_name="other-site")
        responses = client.request([{"moduleName": "Test"}])

        assert len(responses) == 1
