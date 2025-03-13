"""
Wikidotライブラリの共通機能モジュール

このパッケージは、ライブラリ全体で使用される共通機能を提供する。
例外クラス、デコレータ、ロギング機能などの汎用的な機能が含まれる。
"""

from .logger import logger as wd_logger

__all__ = ["wd_logger"]
