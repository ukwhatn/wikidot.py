"""site_permissionsモジュールのユニットテスト"""

import pytest

from wikidot.module.site_permissions import (
    ForumPermissions,
    PagePermissions,
    RatingSettings,
    replace_actors,
)


class TestPagePermissions:
    """PagePermissionsのラウンドトリップ・validateテスト"""

    RAW = "v:armo;c:m;e:m;m:m;d:m;a:m;r:m;z:m;o:rm"

    def test_decode(self):
        perms = PagePermissions.decode(self.RAW)
        assert perms.view == {"anonymous", "registered", "member", "author"}
        assert perms.create == {"member"}
        assert perms.show_options == {"registered", "member"}
        assert perms._unknown == ()

    def test_roundtrip(self):
        perms = PagePermissions.decode(self.RAW)
        assert perms.encode() == self.RAW

    def test_decode_unknown_symbol_preserved(self):
        # "x" is not a documented perm letter; the whole segment must
        # survive the round trip instead of being silently dropped
        raw = "v:armo;x:ar"
        perms = PagePermissions.decode(raw)
        assert perms._unknown == ("x:ar",)
        # unknown segments are re-appended (after the fixed known order)
        assert perms.encode().endswith("x:ar")

    def test_decode_unknown_user_symbol_in_known_perm_preserved(self):
        # "q" is not a documented actor symbol; the whole "letter:users"
        # segment is kept as unknown rather than losing the "q"
        raw = "v:arq"
        perms = PagePermissions.decode(raw)
        assert perms._unknown == ("v:arq",)
        assert perms.view == frozenset()

    def test_validate_no_violation(self):
        perms = PagePermissions.decode(self.RAW)
        assert perms.validate() == []

    def test_validate_anonymous_without_registered(self):
        perms = PagePermissions(view=frozenset({"anonymous"}))
        violations = perms.validate()
        assert len(violations) == 1
        assert "view" in violations[0]

    def test_validate_registered_without_member(self):
        perms = PagePermissions(view=frozenset({"registered"}))
        violations = perms.validate()
        assert len(violations) == 1

    def test_empty_string_roundtrip(self):
        perms = PagePermissions.decode("")
        assert perms.encode() == "v:;c:;e:;m:;d:;a:;r:;z:;o:"


class TestReplaceActors:
    def test_replace_single_field(self):
        base = PagePermissions.decode(TestPagePermissions.RAW)
        updated = replace_actors(base, view={"anonymous"})
        assert updated.view == {"anonymous"}
        # untouched fields survive
        assert updated.create == base.create

    def test_replace_accepts_any_iterable(self):
        base = PagePermissions()
        updated = replace_actors(base, view=["member", "registered"])
        assert updated.view == frozenset({"member", "registered"})


class TestForumPermissions:
    RAW = "t:m;p:armo;e:m"

    def test_roundtrip(self):
        perms = ForumPermissions.decode(self.RAW)
        assert perms.encode() == self.RAW

    def test_unknown_s_symbol_preserved(self):
        # "s" is defined in Wikidot's client JS but not rendered in the
        # permission table on any tested site; must not be dropped
        raw = "t:m;p:armo;e:m;s:ar"
        perms = ForumPermissions.decode(raw)
        assert perms._unknown == ("s:ar",)
        assert perms.encode() == raw


class TestRatingSettings:
    def test_decode_drvm(self):
        rating = RatingSettings.decode("drvM")
        assert rating.enabled is False
        assert rating.voters == "registered"
        assert rating.anonymous is False
        assert rating.kind == "plus_minus"

    def test_roundtrip(self):
        for raw in ("drvM", "eraP", "dmaS"):
            assert RatingSettings.decode(raw).encode() == raw

    def test_decode_invalid_length_raises(self):
        with pytest.raises(ValueError):
            RatingSettings.decode("drv")

    def test_decode_invalid_char_raises(self):
        with pytest.raises(ValueError):
            RatingSettings.decode("xrvM")
