クイックスタート
===========

基本的な使い方
---------

wikidot.pyを使用するための基本的な例を示します。

1. クライアントの初期化
^^^^^^^^^^^^^^^^^

まず、Clientクラスのインスタンスを作成します：

.. code-block:: python

    import wikidot
    
    # ログインなしでの使用
    client = wikidot.Client()
    
    # ログインありでの使用
    client = wikidot.Client(username="your_username", password="your_password")

2. サイトの取得
^^^^^^^^^^

特定のWikidotサイトにアクセスします：

.. code-block:: python

    # サイト名からサイトを取得
    site = client.site.get("scp-jp")
    
    # サイト情報の表示
    print(f"サイト名: {site.name}")
    print(f"説明: {site.description}")

3. ページの操作
^^^^^^^^^

サイト内のページを操作します：

.. code-block:: python

    # ページを取得
    page = site.page.get("scp-173")
    
    # ページ情報の表示
    print(f"タイトル: {page.title}")
    print(f"作成者: {page.created_by.name}")
    print(f"作成日時: {page.created_at}")
    
    # ページソースの取得
    source = page.source
    print(f"ソース: {source.content}")

4. ユーザー情報の取得
^^^^^^^^^^^^^

ユーザー情報を取得します：

.. code-block:: python

    # ユーザー名からユーザーを取得
    user = client.user.get("username")
    
    # ユーザー情報の表示
    print(f"ユーザー名: {user.name}")
    print(f"ユーザーID: {user.id}")
    
    # ユーザーがメンバーのサイト一覧
    for site in user.get_member_sites():
        print(f"サイト: {site.name}")

5. フォーラムの操作
^^^^^^^^^^

フォーラムを操作します：

.. code-block:: python

    # フォーラムカテゴリの取得
    categories = site.forum.categories()
    
    for category in categories:
        print(f"カテゴリ名: {category.name}")
        
        # カテゴリ内のスレッド取得
        threads = category.get_threads()
        for thread in threads:
            print(f"  スレッド: {thread.title}")
            
            # スレッド内の投稿取得
            posts = thread.get_posts()
            for post in posts:
                print(f"    投稿者: {post.created_by.name}")
                print(f"    内容: {post.content[:50]}...")
                
詳細な使用方法については、各モジュールのリファレンスドキュメントを参照してください。