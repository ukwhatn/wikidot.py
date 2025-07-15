インストール方法
==============

PyPIからのインストール
-----------------

wikidot.pyは、PyPIからインストールできます：

.. code-block:: bash

    pip install wikidot

必要条件
------

* Python 3.10以上
* httpx
* beautifulsoup4
* lxml

ログ設定
------

デフォルトではWARNINGレベルでログ出力します。

.. code-block:: python

    from wikidot import Client
    
    # INFOレベルで詳細ログを表示
    client = Client(logging_level="INFO")