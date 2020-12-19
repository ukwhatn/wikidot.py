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

### [**wikidot.page.getdata()**](wikidot.page)

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

- **raise される例外**

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

### [**wikidot.page.getid()**](wikidot.page)

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
- **返り値:**
  - **list**
    - `[(fullname, pageid), .....]`
    - 対象のページが存在しない場合、pageid には None が入ります。

---

### [**wikidot.page.getsource()**](wikidot.page)

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
- **返り値:**
  - **list**
    - `[(pageid, source), .....]`
    - 対象のページが見つからなかった場合や、ソースを閲覧する権限がなかった場合は source に None が入ります。

---

### [**wikidot.page.gethistory()**](wikidot.page)

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

### のこりはあとでかきます