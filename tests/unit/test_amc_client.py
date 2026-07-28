"""AMCクライアントのユニットテスト"""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_httpx import HTTPXMock

from wikidot.common.exceptions import (
    AMCHttpStatusCodeException,
    ForbiddenException,
    FormErrorsException,
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

    def test_try_again_respects_time_to_wait(self, httpx_mock: HTTPXMock) -> None:
        """try_againにtime_to_wait（秒）があればその秒数だけ待つ"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "try_again", "time_to_wait": 3},
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        config = AjaxModuleConnectorConfig(retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)

        with patch("wikidot.connector.ajax.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            client.request([{"moduleName": "Test"}])

        mock_sleep.assert_called_once_with(3.0)

    def test_try_again_time_to_wait_capped_by_max_backoff(self, httpx_mock: HTTPXMock) -> None:
        """time_to_waitがmax_backoffを超える場合は上限で切る（サーバ値を無制限に信用しない）"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "try_again", "time_to_wait": 999},
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        config = AjaxModuleConnectorConfig(retry_interval=0, max_backoff=5.0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)

        with patch("wikidot.connector.ajax.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            client.request([{"moduleName": "Test"}])

        mock_sleep.assert_called_once_with(5.0)

    def test_try_again_without_time_to_wait_uses_backoff(self, httpx_mock: HTTPXMock) -> None:
        """time_to_waitが無い場合は従来の指数バックオフのまま（挙動が変わらないこと）"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "try_again"},
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        config = AjaxModuleConnectorConfig(retry_interval=1.0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)

        with patch("wikidot.connector.ajax.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            client.request([{"moduleName": "Test"}])

        # backoff_factor^(1-1) * 1.0 = 1.0 + jitter(0~10%)
        called_backoff = mock_sleep.call_args[0][0]
        assert 1.0 <= called_backoff <= 1.1

    def test_unknown_action_event_fails_immediately(self, httpx_mock: HTTPXMock) -> None:
        """actionを伴うHTTP 500 + 空ボディはリトライせず即座に失敗する（未対応event検出）"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            status_code=500,
        )

        config = AjaxModuleConnectorConfig(attempt_limit=5, retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)

        with pytest.raises(AMCHttpStatusCodeException):
            client.request([{"moduleName": "Empty", "action": "ManageSiteAction", "event": "noSuchEvent"}])

        # リトライせず1回のみリクエストされていること
        assert len(httpx_mock.get_requests()) == 1

    def test_action_500_with_body_still_retries(self, httpx_mock: HTTPXMock) -> None:
        """actionを伴っていてもボディが空でなければ通常どおりリトライする"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            status_code=500,
            text="Internal Server Error",
        )
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        config = AjaxModuleConnectorConfig(retry_interval=0)
        client = AjaxModuleConnectorClient(site_name="www", config=config)

        client.request([{"moduleName": "Empty", "action": "ManageSiteAction", "event": "saveGeneral"}])

        assert len(httpx_mock.get_requests()) == 2

    def test_list_value_sent_with_bracket_notation(self, httpx_mock: HTTPXMock) -> None:
        """list値を含むbodyはkey[]=v1&key[]=v2形式で送信される（jQuery.param互換）"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        client = AjaxModuleConnectorClient(site_name="www")
        client.request([{"moduleName": "DashboardMessageAction", "selected": [1, 2]}])

        sent_body = httpx_mock.get_requests()[0].content.decode()
        assert "selected%5B%5D=1" in sent_body
        assert "selected%5B%5D=2" in sent_body
        assert "selected=1" not in sent_body

    def test_scalar_body_unaffected_by_bracket_encoding(self, httpx_mock: HTTPXMock) -> None:
        """list値を含まないbodyのエンコード結果は変わらない"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "ok", "body": ""},
        )

        client = AjaxModuleConnectorClient(site_name="www")
        client.request([{"moduleName": "Test", "page_id": 123}])

        sent_body = httpx_mock.get_requests()[0].content.decode()
        assert "page_id=123" in sent_body
        assert "moduleName=Test" in sent_body


class TestAjaxModuleConnectorClientFormErrors:
    """form_errors / form_error ステータスのハンドリングのテスト"""

    def test_form_errors_key_variant(self, httpx_mock: HTTPXMock) -> None:
        """formErrorsキー（多数派: Forum系, Clone, saveGeneral等）"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={
                "status": "form_errors",
                "formErrors": {"name": "Please provide the site title"},
                "message": "Form errors",
            },
        )

        client = AjaxModuleConnectorClient(site_name="www")

        with pytest.raises(FormErrorsException) as exc_info:
            client.request([{"moduleName": "Empty", "action": "ManageSiteAction", "event": "saveGeneral"}])

        assert exc_info.value.errors == {"name": "Please provide the site title"}

    def test_errors_key_variant(self, httpx_mock: HTTPXMock) -> None:
        """errorsキー（WikiPageAction/savePage専用）"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "form_errors", "errors": {"title": "Title is required"}},
        )

        client = AjaxModuleConnectorClient(site_name="www")

        with pytest.raises(FormErrorsException) as exc_info:
            client.request([{"moduleName": "Empty", "action": "WikiPageAction", "event": "savePage"}])

        assert exc_info.value.errors == {"title": "Title is required"}

    def test_message_only_variant(self, httpx_mock: HTTPXMock) -> None:
        """messageのみ（文字列。saveTags・form_error単数形系）"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "form_error", "message": "Invalid tag name"},
        )

        client = AjaxModuleConnectorClient(site_name="www")

        with pytest.raises(FormErrorsException) as exc_info:
            client.request([{"moduleName": "Empty", "action": "WikiPageAction", "event": "saveTags"}])

        assert exc_info.value.errors == {"_message": "Invalid tag name"}

    def test_is_also_a_wikidot_status_code_exception(self, httpx_mock: HTTPXMock) -> None:
        """既存のexcept WikidotStatusCodeExceptionでも捕捉できる（継承関係）"""
        httpx_mock.add_response(
            url="https://www.wikidot.com/ajax-module-connector.php",
            json={"status": "form_errors", "formErrors": {"name": "required"}},
        )

        client = AjaxModuleConnectorClient(site_name="www")

        with pytest.raises(WikidotStatusCodeException):
            client.request([{"moduleName": "Test"}])


class TestAjaxModuleConnectorClientUploadFile:
    """AjaxModuleConnectorClient.upload_file のテスト

    Task 3-5b: /default--flow/files__UploadTarget は実機未検証（wire形式は
    Wikidotのクライアント側JSの読解による）。ここではモックしたHTTPレスポンス
    に対してリクエスト構築とレスポンスパースが正しく行われることのみ検証する。
    """

    def test_upload_file_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://test-site.wikidot.com/default--flow/files__UploadTarget",
            text='<div id="status">ok</div><div id="message">File uploaded.</div><div id="filename">a.txt</div>',
        )

        client = AjaxModuleConnectorClient(site_name="www")
        result = client.upload_file(
            page_id=1,
            filename="a.txt",
            content=b"hello",
            site_name="test-site",
            site_ssl_supported=True,
        )

        assert result == {"status": "ok", "message": "File uploaded.", "filename": "a.txt"}

    def test_upload_file_sends_multipart_fields(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://test-site.wikidot.com/default--flow/files__UploadTarget",
            text='<div id="status">ok</div>',
        )

        client = AjaxModuleConnectorClient(site_name="www")
        client.upload_file(
            page_id=42,
            filename="a.txt",
            content=b"hello",
            site_name="test-site",
            site_ssl_supported=True,
            multikey="mk-1",
        )

        request = httpx_mock.get_requests()[0]
        body_text = request.content.decode()
        assert 'name="action"' in body_text
        assert "FileAction" in body_text
        assert 'name="event"' in body_text
        assert "uploadFile" in body_text
        assert 'name="page_id"' in body_text
        assert "42" in body_text
        assert 'name="source"' in body_text
        assert "multiflash" in body_text
        assert 'name="multikey"' in body_text
        assert "mk-1" in body_text
        assert 'name="userfile"; filename="a.txt"' in body_text

    def test_upload_file_missing_optional_fields(self, httpx_mock: HTTPXMock) -> None:
        """statusのみのレスポンスでもエラーにならない"""
        httpx_mock.add_response(
            url="https://test-site.wikidot.com/default--flow/files__UploadTarget",
            text='<div id="status">fail</div>',
        )

        client = AjaxModuleConnectorClient(site_name="www")
        result = client.upload_file(
            page_id=1,
            filename="a.txt",
            content=b"hello",
            site_name="test-site",
            site_ssl_supported=True,
        )

        assert result == {"status": "fail"}
        assert "message" not in result
        assert "filename" not in result
