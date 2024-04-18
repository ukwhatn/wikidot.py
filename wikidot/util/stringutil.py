import re

from .table import char_table


class StringUtil:
    @staticmethod
    def to_unix(target_str: str) -> str:
        """Unix形式に文字列を変換する

        Parameters
        ----------
        target_str: str
            変換対象の文字列

        Returns
        -------
        str
            変換された文字列
        """
        # MEMO: legacy wikidotの実装に合わせている

        # 特殊文字の変換辞書の作成
        table = str.maketrans(char_table.special_char_map)
        # 変換実施
        target_str = target_str.translate(table)

        # lowercaseへの変換
        target_str = target_str.lower()

        # ascii以外の文字を削除
        target_str = re.sub(r"[^a-z0-9\-:_]", "-", target_str)
        target_str = re.sub(r"^_", ":_", target_str)
        target_str = re.sub(r"(?<!:)_", "-", target_str)
        target_str = re.sub(r"^-*", "", target_str)
        target_str = re.sub(r"-*$", "", target_str)
        target_str = re.sub(r"-{2,}", "-", target_str)
        target_str = re.sub(r":{2,}", ":", target_str)
        target_str = target_str.replace(":-", ":")
        target_str = target_str.replace("-:", ":")
        target_str = target_str.replace("_-", "_")
        target_str = target_str.replace("-_", "_")

        # 先頭と末尾の:を削除
        target_str = re.sub(r"^:", "", target_str)
        target_str = re.sub(r":$", "", target_str)

        return target_str
