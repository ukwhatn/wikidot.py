"""AMCリクエストボディ構築ヘルパー（util.amc_body）のユニットテスト"""

from wikidot.util.amc_body import checkbox, flag, json_param, omit_falsy


class TestCheckbox:
    """checkbox関数のテスト"""

    def test_true_becomes_on(self):
        """Trueは"on"になる（formToArrayのchecked checkbox）"""
        assert omit_falsy(foo=checkbox(True)) == {"foo": "on"}

    def test_false_is_omitted(self):
        """Falseはキーごと省略される（"false"文字列にはならない）"""
        assert omit_falsy(foo=checkbox(False)) == {}

    def test_none_is_omitted(self):
        """Noneも省略される（未指定 = 変更なし）"""
        assert omit_falsy(foo=checkbox(None)) == {}


class TestFlag:
    """flag関数のテスト"""

    def test_true_becomes_true_string(self):
        """Trueは文字列"true"になる（sticky?/block?系のJS個別組み立てパターン）"""
        assert omit_falsy(sticky=flag(True)) == {"sticky": "true"}

    def test_false_is_omitted(self):
        """Falseはキーごと省略される"""
        assert omit_falsy(sticky=flag(False)) == {}

    def test_none_is_omitted(self):
        """Noneも省略される"""
        assert omit_falsy(sticky=flag(None)) == {}


class TestJsonParam:
    """json_param関数のテスト"""

    def test_encodes_dict_as_json_string(self):
        """dictはJSON文字列にエンコードされる"""
        result = json_param({"a": 1})
        assert omit_falsy(categories=result) == {"categories": '{"a": 1}'}

    def test_encodes_list_as_json_string(self):
        """listもJSON文字列にエンコードされる"""
        result = json_param([1, 2, 3])
        assert omit_falsy(options=result) == {"options": "[1, 2, 3]"}

    def test_none_is_omitted(self):
        """Noneは省略される"""
        assert omit_falsy(categories=json_param(None)) == {}


class TestOmitFalsy:
    """omit_falsy関数のテスト"""

    def test_drops_none_values(self):
        """None値のキーは落ちる"""
        result = omit_falsy(a=1, b=None, c="x")
        assert result == {"a": 1, "c": "x"}

    def test_drops_false_values(self):
        """False値のキーも落ちる（httpxがTrue/Falseを"true"/"false"文字列化するため、
        Falseをそのまま送るとWikidotのcheckbox省略規則（キー自体を送らない）に反する）"""
        result = omit_falsy(a=1, b=False, c="x")
        assert result == {"a": 1, "c": "x"}

    def test_keeps_other_falsy_values(self):
        """0や空文字はNone/False（同一性比較）ではないので保持される"""
        result = omit_falsy(a=0, b="")
        assert result == {"a": 0, "b": ""}

    def test_empty_kwargs(self):
        """引数無しなら空dict"""
        assert omit_falsy() == {}

    def test_mixed_with_checkbox_and_flag(self):
        """checkbox/flag/生の値/Noneを混在させても正しくフィルタされる"""
        result = omit_falsy(
            name="test",
            hide_nav=checkbox(False),
            allow_hotlink=checkbox(True),
            sticky=flag(True),
            block=flag(False),
            optional=None,
        )
        assert result == {"name": "test", "allow_hotlink": "on", "sticky": "true"}
