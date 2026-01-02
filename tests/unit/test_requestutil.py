"""RequestUtilのユニットテスト

リトライ機構を持つHTTPリクエスト関数のテストを行う。
"""

from unittest.mock import MagicMock

import httpx
import pytest

from wikidot.connector.ajax import AjaxModuleConnectorConfig
from wikidot.util.requestutil import RequestUtil


class TestRequestUtilGet:
    """RequestUtil.request GETメソッドのテスト"""

    def test_get_success(self, httpx_mock):
        """GET成功"""
        httpx_mock.add_response(url="https://example.com/test1", status_code=200)
        httpx_mock.add_response(url="https://example.com/test2", status_code=200)

        mock_client = MagicMock()
        mock_client.amc_client.config = AjaxModuleConnectorConfig(
            attempt_limit=3,
            retry_interval=0.01,
        )

        results = RequestUtil.request(
            mock_client,
            "GET",
            ["https://example.com/test1", "https://example.com/test2"],
        )

        assert len(results) == 2
        assert all(isinstance(r, httpx.Response) for r in results)
        assert all(r.status_code == 200 for r in results)

    def test_get_retry_on_5xx(self, httpx_mock):
        """GET 5xxエラー後リトライ成功"""
        httpx_mock.add_response(url="https://example.com/test", status_code=500)
        httpx_mock.add_response(url="https://example.com/test", status_code=200)

        mock_client = MagicMock()
        mock_client.amc_client.config = AjaxModuleConnectorConfig(
            attempt_limit=3,
            retry_interval=0.01,
        )

        results = RequestUtil.request(
            mock_client,
            "GET",
            ["https://example.com/test"],
        )

        assert len(results) == 1
        assert results[0].status_code == 200

    def test_get_no_retry_on_4xx(self, httpx_mock):
        """GET 4xxエラーはリトライしない"""
        httpx_mock.add_response(url="https://example.com/test", status_code=404)

        mock_client = MagicMock()
        mock_client.amc_client.config = AjaxModuleConnectorConfig(
            attempt_limit=3,
            retry_interval=0.01,
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            RequestUtil.request(
                mock_client,
                "GET",
                ["https://example.com/test"],
            )

        assert exc_info.value.response.status_code == 404

    def test_get_return_exceptions(self, httpx_mock):
        """return_exceptions=Trueで例外を返す"""
        httpx_mock.add_response(url="https://example.com/test", status_code=404)

        mock_client = MagicMock()
        mock_client.amc_client.config = AjaxModuleConnectorConfig(
            attempt_limit=3,
            retry_interval=0.01,
        )

        results = RequestUtil.request(
            mock_client,
            "GET",
            ["https://example.com/test"],
            return_exceptions=True,
        )

        assert len(results) == 1
        assert isinstance(results[0], httpx.HTTPStatusError)

    def test_get_retry_on_timeout(self, httpx_mock):
        """GETタイムアウト後リトライ成功"""
        httpx_mock.add_exception(httpx.TimeoutException("Timeout"))
        httpx_mock.add_response(url="https://example.com/test", status_code=200)

        mock_client = MagicMock()
        mock_client.amc_client.config = AjaxModuleConnectorConfig(
            attempt_limit=3,
            retry_interval=0.01,
        )

        results = RequestUtil.request(
            mock_client,
            "GET",
            ["https://example.com/test"],
        )

        assert len(results) == 1
        assert results[0].status_code == 200


class TestRequestUtilPost:
    """RequestUtil.request POSTメソッドのテスト"""

    def test_post_success(self, httpx_mock):
        """POST成功"""
        httpx_mock.add_response(url="https://example.com/test", status_code=200, method="POST")

        mock_client = MagicMock()
        mock_client.amc_client.config = AjaxModuleConnectorConfig(
            attempt_limit=3,
            retry_interval=0.01,
        )

        results = RequestUtil.request(
            mock_client,
            "POST",
            ["https://example.com/test"],
        )

        assert len(results) == 1
        assert results[0].status_code == 200

    def test_post_retry_on_5xx(self, httpx_mock):
        """POST 5xxエラー後リトライ成功"""
        httpx_mock.add_response(url="https://example.com/test", status_code=500, method="POST")
        httpx_mock.add_response(url="https://example.com/test", status_code=200, method="POST")

        mock_client = MagicMock()
        mock_client.amc_client.config = AjaxModuleConnectorConfig(
            attempt_limit=3,
            retry_interval=0.01,
        )

        results = RequestUtil.request(
            mock_client,
            "POST",
            ["https://example.com/test"],
        )

        assert len(results) == 1
        assert results[0].status_code == 200

    def test_post_no_retry_on_4xx(self, httpx_mock):
        """POST 4xxエラーはリトライしない"""
        httpx_mock.add_response(url="https://example.com/test", status_code=400, method="POST")

        mock_client = MagicMock()
        mock_client.amc_client.config = AjaxModuleConnectorConfig(
            attempt_limit=3,
            retry_interval=0.01,
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            RequestUtil.request(
                mock_client,
                "POST",
                ["https://example.com/test"],
            )

        assert exc_info.value.response.status_code == 400

    def test_post_retry_on_timeout(self, httpx_mock):
        """POSTタイムアウト後リトライ成功"""
        httpx_mock.add_exception(httpx.TimeoutException("Timeout"), method="POST")
        httpx_mock.add_response(url="https://example.com/test", status_code=200, method="POST")

        mock_client = MagicMock()
        mock_client.amc_client.config = AjaxModuleConnectorConfig(
            attempt_limit=3,
            retry_interval=0.01,
        )

        results = RequestUtil.request(
            mock_client,
            "POST",
            ["https://example.com/test"],
        )

        assert len(results) == 1
        assert results[0].status_code == 200


class TestRequestUtilInvalidMethod:
    """無効なメソッドのテスト"""

    def test_invalid_method_raises(self):
        """無効なメソッドでValueError"""
        mock_client = MagicMock()
        mock_client.amc_client.config = AjaxModuleConnectorConfig(
            attempt_limit=3,
            retry_interval=0.01,
        )

        with pytest.raises(ValueError) as exc_info:
            RequestUtil.request(
                mock_client,
                "DELETE",
                ["https://example.com/test"],
            )

        assert "Invalid method" in str(exc_info.value)
