"""
Wikidotサイトとの対話を行うためのPythonライブラリ

このパッケージはWikidotサイトのAPI操作を抽象化し、直感的なインターフェースを提供する。
ユーザー、サイト、ページなどのWikidotの主要要素にアクセスするための各種クラスが含まれている。
"""

import importlib
import inspect
import os
import sys

from .module.client import Client

__all__ = ["Client"]
__version__ = "3.1.0dev10"


# 全クラス・モジュールを公開する
def _import_submodules():
    """
    パッケージ内の全サブモジュールからクラスをインポートしトップレベルで公開する関数

    各サブディレクトリ内のPythonファイルを走査し、含まれるクラスをトップレベルの名前空間に
    インポートする。これにより、`wikidot.ClassName`のような形式でクラスにアクセスできる。

    Notes
    -----
    '_'で始まるファイル名は無視される。
    インポートに失敗した場合は静かに無視される。
    """
    current_module = sys.modules[__name__]
    package_dir = os.path.dirname(__file__)

    # 公開対象のディレクトリを走査
    for base_dir in ["common", "connector", "module", "util"]:
        base_path = os.path.join(package_dir, base_dir)
        if not os.path.isdir(base_path):
            continue

        for filename in os.listdir(base_path):
            if filename.startswith("_") or not filename.endswith(".py"):
                continue

            module_name = filename[:-3]  # .py を除去
            full_module_name = f"{__name__}.{base_dir}.{module_name}"

            try:
                module = importlib.import_module(full_module_name)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if obj.__module__ == full_module_name:
                        setattr(current_module, name, obj)
            except ImportError:
                pass


_import_submodules()
