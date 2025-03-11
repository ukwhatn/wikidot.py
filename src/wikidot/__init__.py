import importlib
import inspect
import os
import sys

from .module.client import Client


# 全クラス・モジュールを公開する
def _import_submodules():
    current_module = sys.modules[__name__]
    package_dir = os.path.dirname(__file__)

    # 公開対象のディレクトリを走査
    for base_dir in ['common', 'connector', 'module', 'util']:
        base_path = os.path.join(package_dir, base_dir)
        if not os.path.isdir(base_path):
            continue

        for filename in os.listdir(base_path):
            if filename.startswith('_') or not filename.endswith('.py'):
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
