"""page_sourceパーサーのユニットテスト"""

from wikidot.util.parser.page_source import page_source_parse


class TestPageSourceParse:
    """page_source_parse関数のテスト"""

    def test_keeps_consecutive_nbsp_after_link(self) -> None:
        """リンク直後の連続&nbsp;がスペースの個数どおりに復元される"""
        body = (
            '<div class="page-source">\n'
            '\t[[include <a href="/component:image-block">component:image-block</a>&nbsp;&nbsp;<br />\n'
            "name=x.png|<br />\n"
            "]]\n"
            "</div>\n"
        )

        result = page_source_parse(body)

        assert result == "\n\t[[include component:image-block  \nname=x.png|\n]]\n"

    def test_keeps_consecutive_nbsp_in_text(self) -> None:
        """テキスト中・行末の連続&nbsp;がスペースになる"""
        body = '<div class="page-source">mid&nbsp;&nbsp;two<br />\n[[div&nbsp;&nbsp;<br />\n]]</div>'

        assert page_source_parse(body) == "mid  two\n[[div  \n]]"

    def test_keeps_literal_nbsp_character(self) -> None:
        """ソース中の実U+00A0はスペースに変換しない"""
        body = '<div class="page-source">a b&nbsp;c</div>'

        assert page_source_parse(body) == "a b c"

    def test_cjk_text(self) -> None:
        """日本語を含むソースを取得できる"""
        body = '<div class="page-source">見出し&nbsp;&nbsp;<br />\n本文</div>'

        assert page_source_parse(body) == "見出し  \n本文"

    def test_empty_source(self) -> None:
        """空のソースは空文字"""
        assert page_source_parse('<div class="page-source"></div>') == ""

    def test_returns_none_without_source_element(self) -> None:
        """div.page-sourceが無ければNone"""
        assert page_source_parse("<div>no source</div>") is None
