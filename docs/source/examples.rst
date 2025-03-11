使用例
====

基本的な例
------

ここでは、wikidot.pyを使用した具体的な例を紹介します。

クライアント初期化とユーザー操作
-----------------

.. code-block:: python

    import wikidot
    
    # ログインなしでのクライアント初期化
    client = wikidot.Client()
    
    # ログイン情報を指定してクライアント初期化
    authenticated_client = wikidot.Client(
        username="your_username", 
        password="your_password"
    )
    
    # with文を使用した初期化 (セッション終了時に自動的にログアウト)
    with wikidot.Client(username="your_username", password="your_password") as client:
        # ユーザー情報の取得
        user = client.user.get("username")
        print(f"ユーザー名: {user.name}")
        print(f"ユーザーID: {user.id}")
        
        # 複数ユーザーの一括取得
        users = client.user.get_bulk(["user1", "user2", "user3"])
        for user in users:
            print(f"ユーザー: {user.name} (ID: {user.id})")

サイト情報とメンバー管理
--------------

.. code-block:: python

    import wikidot
    
    # クライアントの初期化
    client = wikidot.Client(username="your_username", password="your_password")
    
    # サイトの取得
    site = client.site.get("scp-jp")
    
    # サイト情報の表示
    print(f"サイト名: {site.title}")
    print(f"UNIX名: {site.unix_name}")
    print(f"ドメイン: {site.domain}")
    print(f"URL: {site.get_url()}")
    
    # サイトメンバーの取得
    members = site.members
    print(f"メンバー数: {len(members)}")
    
    # 管理者とモデレーターの取得
    admins = site.admins
    moderators = site.moderators
    
    print(f"管理者数: {len(admins)}")
    print(f"モデレーター数: {len(moderators)}")
    
    # ユーザーをサイトに招待
    user = client.user.get("username")
    site.invite_user(user, "サイトへの招待メッセージ")
    
    # 参加申請の取得と処理
    applications = site.get_applications()
    for application in applications:
        print(f"申請者: {application.user.name}")
        print(f"メッセージ: {application.text}")
        
        # 申請を承認
        application.accept()
        # または拒否
        # application.decline()

ページ操作とページ検索
------------

.. code-block:: python

    import wikidot
    
    # クライアントの初期化
    client = wikidot.Client(username="your_username", password="your_password")
    
    # サイトの取得
    site = client.site.get("scp-jp")
    
    # 特定のページを取得
    page = site.page.get("scp-173")
    print(f"タイトル: {page.title}")
    print(f"作成者: {page.created_by.name}")
    print(f"作成日時: {page.created_at}")
    
    # ソースコードの取得と編集
    source = page.source
    print(f"ソース: {source.content[:100]}...")  # 最初の100文字
    
    # ページの編集
    page.edit(
        source="新しいコンテンツ",
        title="新しいタイトル",
        comment="更新内容の説明"
    )
    
    # ページの検索
    # 特定のカテゴリのページを検索
    category_pages = site.pages.search(category="component")
    
    # タグで検索
    tagged_pages = site.pages.search(tags=["scp", "keter"])
    
    # 複数条件で検索
    search_results = site.pages.search(
        category="_default",
        tags=["euclid", "safe"],
        name="containment",  # ページ名に「containment」を含むものを検索
        order="created_at desc",
        limit=20
    )
    
    # 作成日時で検索 (過去7日間に作成されたページ)
    recent_pages = site.pages.search(
        created_at="> -604800",  # 7日間 = 604800秒
        order="created_at desc"
    )
    
    # 評価の高いページを検索
    top_rated = site.pages.search(
        rating="> 30",  # 評価が30を超えるページ
        order="rating desc",
        limit=10
    )
    
    # 特定のユーザーが作成したページを検索
    user_pages = site.pages.search(
        created_by=user,  # ユーザーオブジェクト
        order="title asc"
    )
    
    # リンク先ページを指定して検索
    linking_pages = site.pages.search(
        link_to="scp-173",  # scp-173にリンクしているページ
    )
    
    # ページの履歴
    revisions = page.get_revisions()
    for rev in revisions[:5]:  # 最新の5つのリビジョン
        print(f"リビジョン: {rev.revision_id}")
        print(f"編集者: {rev.edited_by.name}")
        print(f"編集日時: {rev.edited_at}")
    
    # 特定のリビジョンを取得
    specific_revision = page.get_revision(revision_id=5)
    
    # ページの投票情報
    votes = page.get_votes()
    print(f"評価: {page.rating}")

フォーラム操作
--------

.. code-block:: python

    import wikidot
    
    # クライアントの初期化
    client = wikidot.Client(username="your_username", password="your_password")
    
    # サイトの取得
    site = client.site.get("scp-jp")
    
    # フォーラムカテゴリの取得
    categories = site.forum.categories()
    
    for category in categories:
        print(f"カテゴリ: {category.name}")
        print(f"説明: {category.description}")
        print(f"スレッド数: {category.threads_count}")
        print(f"投稿数: {category.posts_count}")
        
        # カテゴリ内のスレッドを取得
        threads = category.get_threads()
        for thread in threads[:3]:  # 最初の3スレッドを表示
            print(f"  スレッド: {thread.title}")
            print(f"  作成者: {thread.created_by.name}")
            print(f"  作成日時: {thread.created_at}")
            
            # スレッド内の投稿を取得
            posts = thread.get_posts()
            for post in posts[:2]:  # 最初の2投稿を表示
                print(f"    投稿者: {post.created_by.name}")
                print(f"    投稿日時: {post.created_at}")
                print(f"    タイトル: {post.title}")
                print(f"    内容: {post.text[:50]}...")  # 最初の50文字
    
    # 新しいスレッドの作成
    new_thread = category.create_thread(
        title="新しいスレッド",
        content="スレッドの最初の投稿です。"
    )
    
    # スレッドへの返信
    new_post = new_thread.reply(
        title="返信のタイトル",
        content="返信の内容です。"
    )

プライベートメッセージ操作
--------------

.. code-block:: python

    import wikidot
    
    # クライアントの初期化（ログイン必須）
    client = wikidot.Client(username="your_username", password="your_password")
    
    # 受信箱を取得
    inbox = client.private_message.get_inbox()
    print(f"未読メッセージ数: {inbox.unread_count}")
    
    # 最新の受信メッセージを表示
    for message in inbox.messages[:5]:
        print(f"送信者: {message.sender.name}")
        print(f"件名: {message.subject}")
        print(f"日時: {message.sent_at}")
        print(f"内容: {message.body[:100]}...")  # 最初の100文字
    
    # 送信箱を取得
    sentbox = client.private_message.get_sentbox()
    
    # 最新の送信メッセージを表示
    for message in sentbox.messages[:5]:
        print(f"宛先: {message.recipient.name}")
        print(f"件名: {message.subject}")
        print(f"日時: {message.sent_at}")
    
    # 特定のメッセージを取得
    message = client.private_message.get_message(message_id=12345)
    
    # 複数のメッセージを一括取得
    messages = client.private_message.get_messages([12345, 12346, 12347])
    
    # 新しいメッセージを送信
    user = client.user.get("recipient_username")
    client.private_message.send(
        recipient=user,
        subject="メッセージの件名",
        body="メッセージの本文です。"
    )