"""StringUtilのユニットテスト"""

from wikidot.util.stringutil import StringUtil


class TestStringUtilToUnix:
    """StringUtil.to_unix()のテスト"""

    def test_lowercase_conversion(self):
        """大文字を小文字に変換するテスト"""
        assert StringUtil.to_unix("HelloWorld") == "helloworld"
        assert StringUtil.to_unix("UPPERCASE") == "uppercase"
        assert StringUtil.to_unix("MixedCase") == "mixedcase"

    def test_space_to_hyphen(self):
        """空白をハイフンに変換するテスト"""
        assert StringUtil.to_unix("hello world") == "hello-world"
        assert StringUtil.to_unix("multiple  spaces") == "multiple-spaces"

    def test_special_characters_removal(self):
        """特殊文字をハイフンに変換するテスト"""
        assert StringUtil.to_unix("hello!world") == "hello-world"
        assert StringUtil.to_unix("test@example") == "test-example"
        assert StringUtil.to_unix("foo#bar") == "foo-bar"

    def test_leading_trailing_hyphens_removal(self):
        """先頭と末尾のハイフンを削除するテスト"""
        assert StringUtil.to_unix("-hello-") == "hello"
        assert StringUtil.to_unix("---test---") == "test"

    def test_consecutive_hyphens_collapse(self):
        """連続するハイフンを1つに統合するテスト"""
        assert StringUtil.to_unix("hello---world") == "hello-world"
        assert StringUtil.to_unix("a--b--c") == "a-b-c"

    def test_colon_handling(self):
        """コロンの処理テスト"""
        assert StringUtil.to_unix("category:page") == "category:page"
        assert StringUtil.to_unix("a::b") == "a:b"
        assert StringUtil.to_unix(":test:") == "test"

    def test_underscore_prefix_handling(self):
        """アンダースコア接頭辞の処理テスト"""
        # 先頭の_は:_に変換後、先頭:が削除されるため_のまま
        assert StringUtil.to_unix("_test") == "_test"
        # それ以外の_は-に変換される
        assert StringUtil.to_unix("hello_world") == "hello-world"

    def test_special_char_map_conversion(self):
        """特殊文字マッピング変換のテスト"""
        # ドイツ語のウムラウト
        assert StringUtil.to_unix("Ä") == "ae"
        assert StringUtil.to_unix("Ö") == "oe"
        assert StringUtil.to_unix("Ü") == "ue"
        assert StringUtil.to_unix("ß") == "ss"

        # フランス語のアクセント
        assert StringUtil.to_unix("café") == "cafe"
        assert StringUtil.to_unix("naïve") == "naive"

        # ギリシャ文字
        assert StringUtil.to_unix("Θ") == "th"
        assert StringUtil.to_unix("Ψ") == "ps"

    def test_numbers_preserved(self):
        """数字が保持されるテスト"""
        assert StringUtil.to_unix("test123") == "test123"
        assert StringUtil.to_unix("2023年") == "2023"
        assert StringUtil.to_unix("page-001") == "page-001"

    def test_empty_string(self):
        """空文字列のテスト"""
        assert StringUtil.to_unix("") == ""

    def test_complex_cases(self):
        """複合的なケースのテスト"""
        assert StringUtil.to_unix("SCP-001-JP") == "scp-001-jp"
        assert StringUtil.to_unix("Test Page (Draft)") == "test-page-draft"
        # 先頭の_は:_に変換後、先頭:が削除される
        assert StringUtil.to_unix("_admin:config") == "_admin:config"

    def test_japanese_characters_removal(self):
        """日本語文字がハイフンに変換されるテスト"""
        # 日本語はASCII以外なのでハイフンに変換される
        assert StringUtil.to_unix("日本語テスト") == ""
        assert StringUtil.to_unix("test日本語page") == "test-page"

    def test_mixed_unicode_and_ascii(self):
        """UnicodeとASCIIの混合テスト"""
        assert StringUtil.to_unix("Héllo Wörld") == "hello-woerld"
        assert StringUtil.to_unix("Москва") == "moskva"  # ロシア語キリル文字

    def test_colon_hyphen_combinations(self):
        """コロンとハイフンの組み合わせテスト"""
        assert StringUtil.to_unix("a:-b") == "a:b"
        assert StringUtil.to_unix("a-:b") == "a:b"
        # 先頭の_は:_に変換後、先頭:が削除される
        assert StringUtil.to_unix("_:-test") == "_:test"

    def test_underscore_hyphen_combinations(self):
        """アンダースコアとハイフンの組み合わせテスト"""
        # _-の組み合わせは_に統合され、先頭_はそのまま
        assert StringUtil.to_unix("_-test") == "_test"
        # 先頭-は削除、_も-に変換されて削除される
        assert StringUtil.to_unix("-_test") == "test"
