"""例外クラスのユニットテスト"""

import pytest

from wikidot.common.exceptions import (
    AjaxModuleConnectorException,
    AMCHttpStatusCodeException,
    ForbiddenException,
    LoginRequiredException,
    NoElementException,
    NotFoundException,
    ResponseDataException,
    SessionCreateException,
    TargetErrorException,
    TargetExistsException,
    UnexpectedException,
    WikidotException,
    WikidotStatusCodeException,
)


class TestWikidotException:
    """WikidotException基底クラスのテスト"""

    def test_basic_exception(self):
        """基本的な例外メッセージのテスト"""
        exc = WikidotException("test message")
        assert str(exc) == "test message"

    def test_inheritance(self):
        """例外の継承関係のテスト"""
        exc = WikidotException("test")
        assert isinstance(exc, Exception)


class TestUnexpectedException:
    """UnexpectedExceptionのテスト"""

    def test_message(self):
        """例外メッセージのテスト"""
        exc = UnexpectedException("unexpected error")
        assert str(exc) == "unexpected error"

    def test_inheritance(self):
        """継承関係のテスト"""
        exc = UnexpectedException("test")
        assert isinstance(exc, WikidotException)


class TestSessionCreateException:
    """SessionCreateExceptionのテスト"""

    def test_message(self):
        """例外メッセージのテスト"""
        exc = SessionCreateException("login failed")
        assert str(exc) == "login failed"

    def test_inheritance(self):
        """継承関係のテスト"""
        exc = SessionCreateException("test")
        assert isinstance(exc, WikidotException)


class TestLoginRequiredException:
    """LoginRequiredExceptionのテスト"""

    def test_message(self):
        """例外メッセージのテスト"""
        exc = LoginRequiredException("login required")
        assert str(exc) == "login required"

    def test_inheritance(self):
        """継承関係のテスト"""
        exc = LoginRequiredException("test")
        assert isinstance(exc, WikidotException)


class TestAMCHttpStatusCodeException:
    """AMCHttpStatusCodeExceptionのテスト"""

    def test_with_status_code(self):
        """ステータスコード付き例外のテスト"""
        exc = AMCHttpStatusCodeException("HTTP error", 404)
        assert str(exc) == "HTTP error"
        assert exc.status_code == 404

    def test_inheritance(self):
        """継承関係のテスト"""
        exc = AMCHttpStatusCodeException("test", 500)
        assert isinstance(exc, AjaxModuleConnectorException)
        assert isinstance(exc, WikidotException)


class TestWikidotStatusCodeException:
    """WikidotStatusCodeExceptionのテスト"""

    def test_with_status_code(self):
        """ステータスコード付き例外のテスト"""
        exc = WikidotStatusCodeException("Wikidot error", "not_found")
        assert str(exc) == "Wikidot error"
        assert exc.status_code == "not_found"

    def test_inheritance(self):
        """継承関係のテスト"""
        exc = WikidotStatusCodeException("test", "error")
        assert isinstance(exc, AjaxModuleConnectorException)


class TestResponseDataException:
    """ResponseDataExceptionのテスト"""

    def test_message(self):
        """例外メッセージのテスト"""
        exc = ResponseDataException("invalid data")
        assert str(exc) == "invalid data"


class TestNotFoundException:
    """NotFoundExceptionのテスト"""

    def test_message(self):
        """例外メッセージのテスト"""
        exc = NotFoundException("page not found")
        assert str(exc) == "page not found"


class TestTargetExistsException:
    """TargetExistsExceptionのテスト"""

    def test_message(self):
        """例外メッセージのテスト"""
        exc = TargetExistsException("page already exists")
        assert str(exc) == "page already exists"


class TestTargetErrorException:
    """TargetErrorExceptionのテスト"""

    def test_message(self):
        """例外メッセージのテスト"""
        exc = TargetErrorException("operation failed")
        assert str(exc) == "operation failed"


class TestForbiddenException:
    """ForbiddenExceptionのテスト"""

    def test_message(self):
        """例外メッセージのテスト"""
        exc = ForbiddenException("access denied")
        assert str(exc) == "access denied"


class TestNoElementException:
    """NoElementExceptionのテスト"""

    def test_message(self):
        """例外メッセージのテスト"""
        exc = NoElementException("element not found")
        assert str(exc) == "element not found"


class TestExceptionRaising:
    """例外のraiseテスト"""

    def test_raise_and_catch_wikidot_exception(self):
        """WikidotExceptionのraise/catchテスト"""
        with pytest.raises(WikidotException) as exc_info:
            raise WikidotException("test error")
        assert str(exc_info.value) == "test error"

    def test_catch_subclass_as_base(self):
        """サブクラスを基底クラスでcatchするテスト"""
        with pytest.raises(WikidotException):
            raise NotFoundException("not found")

    def test_catch_amc_exception_hierarchy(self):
        """AMC例外階層のcatchテスト"""
        with pytest.raises(AjaxModuleConnectorException):
            raise AMCHttpStatusCodeException("error", 500)

        with pytest.raises(AjaxModuleConnectorException):
            raise WikidotStatusCodeException("error", "code")

        with pytest.raises(AjaxModuleConnectorException):
            raise ResponseDataException("error")
