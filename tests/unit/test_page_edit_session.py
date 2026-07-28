"""PageEditSessionモジュールのユニットテスト"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from wikidot.common import exceptions
from wikidot.module.page_edit_session import PageEditSession

if TYPE_CHECKING:
    from wikidot.module.site import Site


def _mock_response(data: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = data
    return response


class TestPageEditSessionOpen:
    """open() / __enter__ のテスト"""

    def test_open_success_new_page(self, mock_site_no_http: Site) -> None:
        """新規ページのロックを取得できる（page_revision_idなし）"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1", "timeLeft": 900})]
        )

        session = PageEditSession(site=mock_site_no_http, fullname="new-page")
        session.open()

        assert session.lock_id == "L1"
        assert session.lock_secret == "S1"
        assert session.is_existing_page is False
        assert session.revision_id == ""
        assert session.time_left == 900

    def test_open_success_existing_page(self, mock_site_no_http: Site) -> None:
        """既存ページのロックを取得できる（page_revision_idあり）"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        mock_site_no_http.amc_request = MagicMock(
            return_value=[
                _mock_response(
                    {
                        "status": "ok",
                        "lock_id": "L1",
                        "lock_secret": "S1",
                        "page_revision_id": 100,
                        "timeLeft": 900,
                    }
                )
            ]
        )

        session = PageEditSession(site=mock_site_no_http, fullname="existing-page", page_id=1)
        session.open()

        assert session.is_existing_page is True
        assert session.revision_id == "100"

    def test_open_locked_raises(self, mock_site_no_http: Site) -> None:
        """ロック中の場合TargetErrorExceptionを送出"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        mock_site_no_http.amc_request = MagicMock(return_value=[_mock_response({"status": "ok", "locked": True})])

        session = PageEditSession(site=mock_site_no_http, fullname="locked-page")
        with pytest.raises(exceptions.TargetErrorException):
            session.open()

    def test_open_sends_force_lock(self, mock_site_no_http: Site) -> None:
        """force_lock=Trueでforce_lock=yesが送られる"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})]
        )

        session = PageEditSession(site=mock_site_no_http, fullname="p", force_lock=True)
        session.open()

        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert body["force_lock"] == "yes"

    def test_open_omits_page_id_when_none(self, mock_site_no_http: Site) -> None:
        """page_id未指定時はキー自体を送らない"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})]
        )

        session = PageEditSession(site=mock_site_no_http, fullname="new-page")
        session.open()

        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert "page_id" not in body

    def test_section_mode_requires_section(self, mock_site_no_http: Site) -> None:
        """mode="section"でsection未指定はValueError"""
        with pytest.raises(ValueError, match="section"):
            PageEditSession(site=mock_site_no_http, fullname="p", mode="section")

    def test_section_mode_sends_section_param(self, mock_site_no_http: Site) -> None:
        """mode="section"でsectionパラメータが送られる"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})]
        )

        session = PageEditSession(site=mock_site_no_http, fullname="p", mode="section", section=2)
        session.open()

        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert body["section"] == 2
        assert body["mode"] == "section"


class TestPageEditSessionContextManager:
    """__enter__ / __exit__ のテスト"""

    def test_exit_releases_lock_when_not_saved(self, mock_site_no_http: Site) -> None:
        """save()が呼ばれずにwithブロックを抜けるとロックを解放する"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        release_response = _mock_response({"status": "ok"})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [release_response]])

        with PageEditSession(site=mock_site_no_http, fullname="p") as session:
            assert session.lock_id == "L1"

        assert mock_site_no_http.amc_request.call_count == 2
        release_body = mock_site_no_http.amc_request.call_args_list[1][0][0][0]
        assert release_body["event"] == "removePageEditLock"

    def test_exit_does_not_release_after_successful_save(self, mock_site_no_http: Site) -> None:
        """save()成功後はロックを解放しない"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        save_response = _mock_response({"status": "ok"})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [save_response]])

        with PageEditSession(site=mock_site_no_http, fullname="p") as session:
            session.save(title="t", source="s")

        assert mock_site_no_http.amc_request.call_count == 2

    def test_exit_releases_lock_on_exception(self, mock_site_no_http: Site) -> None:
        """withブロック内で例外が発生した場合もロックを解放する"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        release_response = _mock_response({"status": "ok"})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [release_response]])

        with pytest.raises(ValueError), PageEditSession(site=mock_site_no_http, fullname="p") as session:
            assert session.lock_id == "L1"
            raise ValueError("boom")

        assert mock_site_no_http.amc_request.call_count == 2

    def test_enter_failure_does_not_call_exit_release(self, mock_site_no_http: Site) -> None:
        """__enter__自体が失敗した場合は解放リクエストを送らない（ロック未取得のため）"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        mock_site_no_http.amc_request = MagicMock(return_value=[_mock_response({"status": "ok", "locked": True})])

        with pytest.raises(exceptions.TargetErrorException), PageEditSession(site=mock_site_no_http, fullname="p"):
            pass

        assert mock_site_no_http.amc_request.call_count == 1


class TestPageEditSessionSave:
    """save() のテスト"""

    def test_save_success(self, mock_site_no_http: Site) -> None:
        """保存が成功する"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        save_response = _mock_response({"status": "ok", "revisionId": 999})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [save_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        data = session.save(title="t", source="s", comment="c")

        assert data["revisionId"] == 999
        assert session._saved is True

    def test_save_status_not_ok_raises(self, mock_site_no_http: Site) -> None:
        """statusが"ok"以外の場合WikidotStatusCodeException"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        save_response = _mock_response({"status": "no_permission"})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [save_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        with pytest.raises(exceptions.WikidotStatusCodeException):
            session.save()

    def test_save_no_lock_error_raises(self, mock_site_no_http: Site) -> None:
        """noLockErrorが立っている場合TargetErrorException"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        save_response = _mock_response({"status": "ok", "noLockError": True, "body": "lost", "nonrecoverable": True})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [save_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        with pytest.raises(exceptions.TargetErrorException):
            session.save()

    def test_save_before_open_raises(self, mock_site_no_http: Site) -> None:
        """openせずにsave()を呼ぶとUnexpectedException"""
        session = PageEditSession(site=mock_site_no_http, fullname="p")
        with pytest.raises(exceptions.UnexpectedException):
            session.save()

    def test_save_and_continue_sends_yes(self, mock_site_no_http: Site) -> None:
        """and_continue=Trueでand_continue=yesが送られる"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        save_response = _mock_response({"status": "ok"})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [save_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        session.save(and_continue=True)

        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert body["and_continue"] == "yes"

    def test_save_omits_optional_falsy_params(self, mock_site_no_http: Site) -> None:
        """range_start/range_end/tags/parentPage/dont_notify_watchers未指定時はキーを送らない"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        save_response = _mock_response({"status": "ok"})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [save_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        session.save()

        body = mock_site_no_http.amc_request.call_args[0][0][0]
        for key in ("range_start", "range_end", "tags", "parentPage", "dont_notify_watchers", "and_continue"):
            assert key not in body


class TestPageEditSessionSynchronize:
    """synchronize() のテスト"""

    def test_synchronize_updates_time_left(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        sync_response = _mock_response({"status": "ok", "timeLeft": 850})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [sync_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        session.synchronize(since_last_input=10)

        assert session.time_left == 850

    def test_synchronize_lock_recreated_updates_lock(self, mock_site_no_http: Site) -> None:
        """lockRecreated時にlock_id/lock_secretが差し替わる"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        sync_response = _mock_response(
            {"status": "ok", "lockRecreated": True, "lockId": "L2", "lockSecret": "S2", "timeLeft": 900}
        )
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [sync_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        session.synchronize()

        assert session.lock_id == "L2"
        assert session.lock_secret == "S2"

    def test_synchronize_no_lock_error_raises(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        sync_response = _mock_response({"status": "ok", "noLockError": True})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [sync_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        with pytest.raises(exceptions.TargetErrorException):
            session.synchronize()


class TestPageEditSessionRelease:
    """release() のテスト"""

    def test_release_noop_when_not_open(self, mock_site_no_http: Site) -> None:
        """openしていないセッションのrelease()は何もしない"""
        mock_site_no_http.amc_request = MagicMock()
        session = PageEditSession(site=mock_site_no_http, fullname="p")
        session.release()
        mock_site_no_http.amc_request.assert_not_called()

    def test_release_failure_does_not_raise(self, mock_site_no_http: Site) -> None:
        """解放リクエスト自体が失敗しても例外を送出しない"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        mock_site_no_http.amc_request = MagicMock(
            side_effect=[[lock_response], exceptions.ForbiddenException("no permission")]
        )

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        session.release()  # 例外を送出しない


class TestPageEditSessionMisc:
    """check_draft_exists / force_lock_intercept / recreate_expired_lock / preview / diff"""

    def test_check_draft_exists_true(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        check_response = _mock_response({"status": "ok", "draftExists": True})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [check_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        assert session.check_draft_exists() is True

    def test_force_lock_intercept_updates_lock(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        intercept_response = _mock_response({"lock_id": "L3", "lock_secret": "S3", "timeLeft": 900})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [intercept_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        session.force_lock_intercept()

        assert session.lock_id == "L3"
        assert session.lock_secret == "S3"

    def test_recreate_expired_lock_updates_lock(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        recreate_response = _mock_response(
            {"status": "ok", "lockRecreated": True, "lockId": "L4", "lockSecret": "S4", "timeLeft": 900}
        )
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [recreate_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        session.recreate_expired_lock()

        assert session.lock_id == "L4"
        assert session.lock_secret == "S4"

    def test_preview_returns_body_and_title(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        preview_response = _mock_response({"status": "ok", "body": "<p>preview</p>", "title": "T"})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [preview_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        result = session.preview(title="T", source="s")

        assert result["body"] == "<p>preview</p>"
        assert result["title"] == "T"

    def test_diff_returns_body(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()
        lock_response = _mock_response({"status": "ok", "lock_id": "L1", "lock_secret": "S1"})
        diff_response = _mock_response({"status": "ok", "body": "<div>diff</div>"})
        mock_site_no_http.amc_request = MagicMock(side_effect=[[lock_response], [diff_response]])

        session = PageEditSession(site=mock_site_no_http, fullname="p").open()
        result = session.diff(source="s")

        assert result == "<div>diff</div>"
