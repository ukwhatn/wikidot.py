# wikidot.py

Wikidot の ajax-module-connector.php へのリクエストとその結果のパースを簡単に行えるようにしたパッケージです。

# インストール

**Python 3.9 以降が必要です** (`str.removesuffix()`を使用しているため)

```
pip install git+https://github.com/SCP-JP/ukwhatn_wikidot.py
```

その際、以下の依存パッケージが同時にインストールされます

- **bs4** - 0.0.1
- **feedparser** - 6.0.2
- **httpx** - 0.16.1

# 使い方

```python
import wikidot
```

**全ての関数は、キーワード引数のみを受け付けます。**

### [**wikidot.user.login()**](wikidot.user.py)
- Wikidotにログインリクエストを行い、セッションを作成します。
- セッション作成後、`dashboard/settings/DSAccountModule`にリクエストを行い、セッションが正常に作成されたかを判定します。
- **このパッケージを使ったコードを共有する際、この関数の引数、特にpasswordはマスクしてください。**
- **引数:**
  - **user: str**
    - WikidotのユーザーIDを指定します。
  - **password: str**
    - Wikidotのアカウントパスワードを指定します。

- **返り値**
  - **bool**
    - ログインに成功したらTrueが返されます。

---

### [**wikidot.user.logout()**](wikidot.user.py)
- Wikidotからログアウトし、セッションを削除します。
- **引数:**
  - なし

- **返り値**
  - **bool**
    - ログインに成功したらTrue、失敗したらFalseを返します。
    - 主にコードの最後で使用される関数であるため、例外をraiseしません。

---

### [**wikidot.page.getdata()**](wikidot.page.py)

- ListPages モジュールからデータを取得し、辞書にして返します。
- リストが複数ページに渡る場合、全てのページを自動的に取得します。
- **引数:**
  - **limit: int**
    - by default: `10`
    - 複数ページに渡る際の非同期実行の上限(`asyncio.Semaphore()`)を設定します。10 くらいがベストっぽいです。
  - **url: str**
    - リクエストを行うサイトの URL を指定します。`http://[HERE]/ajax-module-connector.php`にそのまま代入されます。
    - eg: `"scp-jp.wikidot.com"`, `"www.scpwiki.com"`
  - **main_key: str**
    - by default: `"fullname"`
    - 返り値の辞書のトップレベルキーを指定します。
    - 値は ListPagesModule の body に与えられるもの(%は省略)、かつ module_body 引数のリストに含まれている必要があります。
    - eg: `"fullname"`, `"created_by_unix"`
  - **module_body: list[str]**
    - by default: ほぼすべての値
    - 取得する値のリストを与えます。値は ListPagesModule の body に与えられるもの(%は省略)である必要があります。
    - 例えば、fullname しか取得する必要がないときは`["fullname"]`、fullname と title が知りたいときには`["fullname", "title"]`を値にします。
  - **<listpages_module_arguments>**
    - "category"や"created_by"など、ListPages モジュールに与えることができる[Selecting pages 引数](https://www.wikidot.com/doc-modules:listpages-module#toc2)をそのまま指定できます。
    - Selecting Pages 引数以外は指定しないでください。場合によってはパースに失敗します。
    - これらの値は、kwargs としてリクエストデータにマージされます。
    - **perpage", "separate", **
    - 例:
      - `wikidot.page.getdata(url="scp-jp.wikidot.com", category="_default", created_by="ukwhatn")`

- **例外:**
  - **wikidot.exceptions.ArgumentsError(msg, reason)**
    - 主に main_key の値が module_body にない場合に raise されます
  - **wikidot.exceptions.StatusIsNotOKError(msg, wd_status_code)**
    - Wikidot からの Response データに含まれる status が"ok"でなかった場合に raise されます。その際の status は e.args[1]で取得できます。
    - Private サイトに対してリクエストを行った際などには"not_ok"ステータスが返ってくるため、raise されます。

- **返り値**
  - 日付は datetime、`created/commented/updated_by_id`は Optional[int]、その他の数値データは int、その他は str 型で返されます。

```python
{
    <トップレベルキーに対応する値>: {
        "fullname": fullname(str),
        "title": title(str),
        ......
    },
    ......
}
# 例:
{
    "scp-001-jp": {
        "fullname": "scp-001-jp",
        "title": "SCP-001-JP",
        ......
    },
    ......
}
```

---

### [**wikidot.page.getid()**](wikidot.page.py)

- 対象のページに noredirect,norender でアクセスし、ヘッダーに含まれる PageID を取得します。
- **引数:**
  - **limit: int**
    - by default: `10`
    - 複数ページを取得する際の非同期実行の上限(`asyncio.Semaphore()`)を設定します。10 くらいがベストっぽいです。
  - **url: str**
    - リクエストを行うサイトの URL を指定します。`http://[HERE]/ajax-module-connector.php`にそのまま代入されます。
    - eg: `"scp-jp.wikidot.com"`, `"www.scpwiki.com"`
  - **targets: list[str]**
    - 対象ページの fullname をリストにして渡してください。
    - eg: `targets=["scp-001-jp"]`, `targets=["scp-001-jp", "scp-002-jp", "component:theme"]`
- **例外:**
  - **wikidot.exceptions.UnexpectedError(msg, reason)**
    - HTTPリクエスト中に予期していない例外が発生した場合にraiseされます。
    - 第２引数には"undefined"が入ります。
- **返り値:**
  - **list**
    - `[(fullname, pageid), .....]`
    - 対象のページが存在しない場合、pageid には None が入ります。

---

### [**wikidot.page.getsource()**](wikidot.page.py)

- 対象のページのソースを取得します。
- **引数:**
  - **limit: int**
    - by default: `10`
    - 複数ページを取得する際の非同期実行の上限(`asyncio.Semaphore()`)を設定します。10 くらいがベストっぽいです。
  - **url: str**
    - リクエストを行うサイトの URL を指定します。`http://[HERE]/ajax-module-connector.php`にそのまま代入されます。
    - eg: `"scp-jp.wikidot.com"`, `"www.scpwiki.com"`
  - **targets: list[int]**
    - 対象ページの**PageID**をリストにして渡してください。
    - eg: `targets=[123456]`, `targets=[123456, 123457, 123458]`
- **例外:**
  - **wikidot.exceptions.StatusIsNotOKError(msg, status)**
    - Wikidot からの Response データに含まれる status が"ok"でなかった場合に raise されます。その際の status は e.args[1]で取得できます。
    - **"no_page"(対象のページが存在しない)や"no_permission"(対象のページソースを閲覧できない)が返ってきた場合はraiseされず、sourceにNoneが入ります。**
  - **wikidot.exceptions.UnexpectedError(msg, reason)**
    - HTTPリクエスト中に予期していない例外が発生した場合にraiseされます。
    - 第２引数には"undefined"が入ります。
- **返り値:**
  - **list**
    - `[(pageid, source), .....]`
    - 対象のページが見つからなかった場合や、ソースを閲覧する権限がなかった場合は source に None が入ります。

---

### [**wikidot.page.gethistory()**](wikidot.page.py)

- 対象のページの全てのリビジョンデータを取得します。
- **引数:**
  - **limit: int**
    - by default: `10`
    - 複数ページを取得する際の非同期実行の上限(`asyncio.Semaphore()`)を設定します。10 くらいがベストっぽいです。
  - **url: str**
    - リクエストを行うサイトの URL を指定します。`http://[HERE]/ajax-module-connector.php`にそのまま代入されます。
    - eg: `"scp-jp.wikidot.com"`, `"www.scpwiki.com"`
  - **targets: list[int]**
    - 対象ページの**PageID**をリストにして渡してください。
    - eg: `targets=[123456]`, `targets=[123456, 123457, 123458]`
- **返り値:**
  - **list**
    - "flags"は、"new", "source", "title", "rename", "tag", "meta", "file", "undefined"のうち、該当するもののリストです。
```python
[
    (
        PageID(int), (
            {
                "rev_id": RevisionID(int),
                "rev_no": RevisionNo(int),
                "author": {
                    "name": author_name(str),
                    "unix": author_unix(str),
                    "id": author_id(int)
                },
                "time": time_edited(datetime),
                "flags": flags(list),
                "comment": comment(Optional[str])
            },
            ......revs
        )
    ),
    ......pages
]
```

---

### [**wikidot.page.edit()**](wikidot.page.py) | **SESSION REQUIRED**

- 対象のページを編集、あるいは新規作成します。
- ページを新規作成したいときはpageid引数をNoneにしてください。pageidがNoneだった場合自動でpageidの取得を試み、対象ページが存在するか否かを判断します。
- 非同期に実行するとtry_againステータスが返ってきやすいので、あえてしていません。
- **引数:**
  - **url: str**
    - リクエストを行うサイトの URL を指定します。`http://[HERE]/ajax-module-connector.php`にそのまま代入されます。
    - eg: `"scp-jp.wikidot.com"`, `"www.scpwiki.com"`
  - **fullname: str**
    - 対象ページの**fullname**を指定します。
  - **pageid: Optional[int]**
    - by default: None
    - 対象のページの**PageID**を指定します。不明・新規ページである場合はNoneにすると、関数内で自動取得します。
  - **title: str**
    - by default: ""
    - 対象のページのページタイトルを指定します。
  - **content: str**
    - by default: ""
    - 対象のページの内容部分をWikidot構文で指定します。
  - **comment: str**
    - by default: ""
    - "編集の概要"部分を指定します。
  - **forceedit: bool**
    - by default: False
    - 対象のページの編集がロックされていた場合に強制解除を試みるかどうかを指定します。
    - この値がFalse、かつ対象のページが編集中だった場合、`wikidot.exceptions.StatusIsNotOKError`がraiseされます。
- **返り値:**
  - なし

----

### [**wikidot.page.rename()**](wikidot.page.py) | **SESSION REQUIRED**
- ページを一括リネームします。
- **引数:**
  - **limit: int**
    - by default: `10`
    - 複数ページを取得する際の非同期実行の上限(`asyncio.Semaphore()`)を設定します。10 くらいがベストっぽいです。
  - **url: str**
    - リクエストを行うサイトの URL を指定します。`http://[HERE]/ajax-module-connector.php`にそのまま代入されます。
    - eg: `"scp-jp.wikidot.com"`, `"www.scpwiki.com"`
  - **targets: list[list[pageid, str]]**
    - 対象ページの**PageID**とリネーム後の**fullname**のタプルをリストにして渡してください。
    - eg: `targets=[(123456, page1)]`, `targets=[(123456, page1), (1234567, page11)]`
- **返り値**
  - なし

----

### [**wikidot.page.setparent()**](wikidot.page.py) | **SESSION REQUIRED**
- 親ページを一括設定します。
- **引数:**
  - **limit: int**
    - by default: `10`
    - 複数ページを取得する際の非同期実行の上限(`asyncio.Semaphore()`)を設定します。10 くらいがベストっぽいです。
  - **url: str**
    - リクエストを行うサイトの URL を指定します。`http://[HERE]/ajax-module-connector.php`にそのまま代入されます。
    - eg: `"scp-jp.wikidot.com"`, `"www.scpwiki.com"`
  - **targets: list[list[pageid, str]]**
    - 対象ページの**PageID**と親ページの**fullname**のタプルをリストにして渡してください。
    - eg: `targets=[(123456, page1)]`, `targets=[(123456, page1), (1234567, page11)]`
- **返り値**
  - なし

----

### [**wikidot.page.setparent()**](wikidot.forum.py)
- フォーラムのカテゴリ名とカテゴリIDを全て取得します。
- **引数:**
  - **url: str**
    - リクエストを行うサイトのURLを指定します。`http://[HERE]/ajax-module-connector.php`にそのまま代入されます。
    - eg: `"scp-jp.wikidot.com"`, `"www.scpwiki.com"`
  - **includehidden: bool**
    - by default: True
    - 隠しカテゴリを含むかを指定します。
- **返り値**
  - **list**
    - カテゴリIDとカテゴリ名のタプルのリストです。
    - `[(cat_id, cat_name), .....]`

----

### [**wikidot.page.getthreadspercategory()**](wikidot.forum.py)
- **引数:**
  - **limit: int**
    - by default: `10`
    - 複数ページを取得する際の非同期実行の上限(`asyncio.Semaphore()`)を設定します。10 くらいがベストっぽいです。
  - **url: str**
    - リクエストを行うサイトの URL を指定します。`http://[HERE]/ajax-module-connector.php`にそのまま代入されます。
    - eg: `"scp-jp.wikidot.com"`, `"www.scpwiki.com"`
  - **categoryid: int**
    - 対象のカテゴリIDを指定します。
- **返り値**
  - **dict**
    - ユーザーの扱い
      - 削除済: name:"account deleted", unix:"account_deleted", id: ユーザーID
      - ゲスト: name,unix:表示に準ずる, id:None
      - Wikidot作成スレッド: name:"Wikidot", unix:"wikidot", id:None
```
{
  threadid: {
    "title": スレッド名(str),
    "author": {
      "author_id": スレッド作成ユーザーのID(int),
      "author_unix": スレッド作成ユーザーのunix名(str),
      "author_name": スレッド作成ユーザー名(str)
    },
    "posts": number-of-posts(int),
    "start": datetime-thread-started(datetime)
  },
  ....
}
```

----

### [**wikidot.page.getthreads()**](wikidot.forum.py)
- サイト上の全てのスレッドを取得します。
- **引数:**
  - **limit: int**
    - by default: `10`
    - 複数ページを取得する際の非同期実行の上限(`asyncio.Semaphore()`)を設定します。10 くらいがベストっぽいです。
  - **url: str**
    - リクエストを行うサイトの URL を指定します。`http://[HERE]/ajax-module-connector.php`にそのまま代入されます。
    - eg: `"scp-jp.wikidot.com"`, `"www.scpwiki.com"`
  - **includehidden: bool**
    - by default: True
    - 隠しカテゴリを含むかを指定します。
- **返り値**
  - **list**
```
[
  {
    "category_id": カテゴリID(int),
    "category_title": カテゴリ名(str),
    "category_threads": getthreadspercategory()の返り値
  },
  ......
]
```

----

### [**wikidot.page.getposts()**](wikidot.forum.py)
- スレッド内の全てのポストを取得します。

----

### [**wikidot.page.getparentpage()**](wikidot.forum.py)
- perPageDiscussionの親ページのfullnameとpageidを取得します。

----

### [**wikidot.page.getpagediscussion()**](wikidot.forum.py)
- ページのperpagediscussionのスレッドIDを取得します。

----

### [**wikidot.page.post()**](wikidot.forum.py)
- ディスカッションにポストを行います

----

### [**wikidot.page.edit()**](wikidot.forum.py)
- ディスカッションポストを編集します。

----

### [**wikidot.page.rss()**](wikidot.forum.py)
- RSSフィードを取得・パースします

----

### [**wikidot.tag.set_with_pageid()**](wikidot.tag.py)
### [**wikidot.tag.set_with_fullname()**](wikidot.tag.py)
- 対象ページのタグを設定します。

----

### [**wikidot.tag.replace()**](wikidot.tag.py)
- タグを置き換えます。

----

### [**wikidot.tag.reset()**](wikidot.tag.py)
- 対象ページ群のタグを一括設定します。

----

### [**wikidot.vote.getvoter()**](wikidot.vote.py)
- 対象ページへのVoterとUV/DVを取得します。

----

### [**wikidot.vote.postvote()**](wikidot.vote.py)
- 対象ページにVoteを行います。

----

### [**wikidot.vote.cancelvote()**](wikidot.vote.py)
- 対象ページへのVoteをキャンセルします。

----

### [**wikidot.site.getmembers()**](wikidot.site.py)
- 対象サイトのメンバーを全件取得します。

----

### [**wikidot.site.gethistory()**](wikidot.site.py)
- 対象サイトの全リビジョン、あるいはlimitpage引数の値*1000個のリビジョンを取得します。

----

### [**wikidot.file.getlist()**](wikidot.file.py)
- 対象ページにアップロードされているファイルを全て取得します。

----
