"""
Sphinx設定ファイル

このファイルはSphinxドキュメントのビルド設定を定義する。
GitHub Pagesでの公開を前提とした設定になっている。
"""

import os
import sys
from datetime import datetime

# sys.pathにソースコードディレクトリを追加
sys.path.insert(0, os.path.abspath('../../src'))

# ソースコードのエンコーディング設定
source_encoding = 'utf-8'

# モックライブラリ設定（インポートエラー回避）
autodoc_mock_imports = ['httpx', 'bs4', 'lxml']

# プロジェクト情報
project = 'wikidot.py'
copyright = f'{datetime.now().year}, ukwhatn'
author = 'ukwhatn'

# バージョン情報
try:
    import wikidot
    version = wikidot.__version__ if hasattr(wikidot, '__version__') else '3.1.0.dev9'
except (ImportError, AttributeError):
    version = '3.1.0.dev9'
release = version

# 拡張機能
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints',
    'myst_parser',
]

# テンプレートパス
templates_path = ['_templates']

# 除外パターン
exclude_patterns = []

# デフォルト言語
language = 'ja'

# HTMLテーマ
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'navigation_depth': 4,
    'titles_only': False,
}

# 静的ファイルのパス
html_static_path = ['_static']

# インタースフィンクス設定
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'httpx': ('https://www.python-httpx.org/', None),
    'bs4': ('https://www.crummy.com/software/BeautifulSoup/bs4/doc/', None),
}

# autodoc設定
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
autodoc_preserve_defaults = True

# Napoleon設定（Numpyスタイルのdocstring用）
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_type_aliases = None

# MyST設定
myst_enable_extensions = [
    'colon_fence',
]

# GitHub Pagesの設定
html_baseurl = 'https://ukwhatn.github.io/wikidot.py/'