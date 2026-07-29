"""PageFileモジュールのユニットテスト"""

from unittest.mock import MagicMock

from wikidot.module.page_file import PageFile, PageFileCollection


class TestPageFileCollection:
    """PageFileCollectionのテスト"""

    def test_init_with_page(self):
        """ページを指定して初期化"""
        page = MagicMock()

        collection = PageFileCollection(page=page, files=[])

        assert collection.page == page
        assert len(collection) == 0

    def test_init_infers_page_from_files(self):
        """ファイルリストからページを推測"""
        page = MagicMock()
        file1 = PageFile(page=page, id=1, name="test.txt", url="", mime_type="", size=0)

        collection = PageFileCollection(page=None, files=[file1])

        assert collection.page == page

    def test_init_with_files(self):
        """ファイルリストを指定して初期化"""
        page = MagicMock()
        file1 = PageFile(page=page, id=1, name="test.txt", url="", mime_type="", size=100)
        file2 = PageFile(page=page, id=2, name="image.png", url="", mime_type="", size=200)

        collection = PageFileCollection(page=page, files=[file1, file2])

        assert len(collection) == 2

    def test_iter(self):
        """イテレーション"""
        page = MagicMock()
        file1 = PageFile(page=page, id=1, name="a.txt", url="", mime_type="", size=0)
        file2 = PageFile(page=page, id=2, name="b.txt", url="", mime_type="", size=0)

        collection = PageFileCollection(page=page, files=[file1, file2])

        files = list(collection)
        assert len(files) == 2
        assert files[0].name == "a.txt"
        assert files[1].name == "b.txt"

    def test_find_existing_by_id(self):
        """IDで存在するファイルを検索"""
        page = MagicMock()
        file1 = PageFile(page=page, id=123, name="test.txt", url="", mime_type="", size=0)
        file2 = PageFile(page=page, id=456, name="other.txt", url="", mime_type="", size=0)

        collection = PageFileCollection(page=page, files=[file1, file2])

        result = collection.find(123)

        assert result is not None
        assert result.name == "test.txt"

    def test_find_nonexistent_by_id(self):
        """存在しないIDの検索でNone"""
        page = MagicMock()
        file1 = PageFile(page=page, id=123, name="test.txt", url="", mime_type="", size=0)

        collection = PageFileCollection(page=page, files=[file1])

        result = collection.find(999)

        assert result is None

    def test_find_by_name_existing(self):
        """名前で存在するファイルを検索"""
        page = MagicMock()
        file1 = PageFile(page=page, id=1, name="image.png", url="", mime_type="", size=0)
        file2 = PageFile(page=page, id=2, name="document.pdf", url="", mime_type="", size=0)

        collection = PageFileCollection(page=page, files=[file1, file2])

        result = collection.find_by_name("document.pdf")

        assert result is not None
        assert result.id == 2

    def test_find_by_name_nonexistent(self):
        """存在しない名前の検索でNone"""
        page = MagicMock()
        file1 = PageFile(page=page, id=1, name="image.png", url="", mime_type="", size=0)

        collection = PageFileCollection(page=page, files=[file1])

        result = collection.find_by_name("nonexistent.txt")

        assert result is None


class TestPageFileCollectionParseSize:
    """PageFileCollection._parse_sizeのテスト"""

    def test_parse_bytes(self):
        """バイト単位のパース"""
        result = PageFileCollection._parse_size("500 Bytes")
        assert result == 500

    def test_parse_kilobytes(self):
        """キロバイト単位のパース"""
        result = PageFileCollection._parse_size("1.5 kB")
        assert result == 1500

    def test_parse_megabytes(self):
        """メガバイト単位のパース"""
        result = PageFileCollection._parse_size("2 MB")
        assert result == 2000000

    def test_parse_gigabytes(self):
        """ギガバイト単位のパース"""
        result = PageFileCollection._parse_size("1 GB")
        assert result == 1000000000

    def test_parse_unknown_returns_zero(self):
        """不明な単位は0を返す"""
        result = PageFileCollection._parse_size("unknown")
        assert result == 0

    def test_parse_with_whitespace(self):
        """空白を含む文字列のパース"""
        result = PageFileCollection._parse_size("  100 Bytes  ")
        assert result == 100


class TestPageFileCollectionAcquire:
    """PageFileCollection.acquireのテスト"""

    def test_acquire_success(self):
        """ファイル取得成功"""
        page = MagicMock()
        page.id = 12345
        site = MagicMock()
        site.url = "https://test.wikidot.com"
        page.site = site

        response = MagicMock()
        response.json.return_value = {
            "body": """
                <table class="page-files">
                    <tbody>
                        <tr id="file-row-100">
                            <td><a href="/local--files/test-page/image.png">image.png</a></td>
                            <td><span title="image/png">PNG</span></td>
                            <td>1.5 kB</td>
                        </tr>
                    </tbody>
                </table>
            """
        }
        site.amc_request.return_value = [response]

        collection = PageFileCollection.acquire(page)

        assert len(collection) == 1
        assert collection[0].id == 100
        assert collection[0].name == "image.png"
        assert collection[0].mime_type == "image/png"
        assert collection[0].size == 1500
        assert "test.wikidot.com" in collection[0].url

    def test_acquire_empty(self):
        """ファイルなしの場合"""
        page = MagicMock()
        page.id = 12345
        site = MagicMock()
        page.site = site

        response = MagicMock()
        response.json.return_value = {"body": "<div>No files</div>"}
        site.amc_request.return_value = [response]

        collection = PageFileCollection.acquire(page)

        assert len(collection) == 0
        assert collection.page == page

    def test_acquire_multiple_files(self):
        """複数ファイルの取得"""
        page = MagicMock()
        page.id = 12345
        site = MagicMock()
        site.url = "https://test.wikidot.com"
        page.site = site

        response = MagicMock()
        response.json.return_value = {
            "body": """
                <table class="page-files">
                    <tbody>
                        <tr id="file-row-100">
                            <td><a href="/local--files/test-page/file1.txt">file1.txt</a></td>
                            <td><span title="text/plain">TXT</span></td>
                            <td>500 Bytes</td>
                        </tr>
                        <tr id="file-row-101">
                            <td><a href="/local--files/test-page/file2.pdf">file2.pdf</a></td>
                            <td><span title="application/pdf">PDF</span></td>
                            <td>2 MB</td>
                        </tr>
                    </tbody>
                </table>
            """
        }
        site.amc_request.return_value = [response]

        collection = PageFileCollection.acquire(page)

        assert len(collection) == 2
        assert collection[0].name == "file1.txt"
        assert collection[1].name == "file2.pdf"

    def test_acquire_skips_invalid_rows(self):
        """無効な行はスキップ"""
        page = MagicMock()
        page.id = 12345
        site = MagicMock()
        site.url = "https://test.wikidot.com"
        page.site = site

        response = MagicMock()
        response.json.return_value = {
            "body": """
                <table class="page-files">
                    <tbody>
                        <tr id="file-row-100">
                            <td><a href="/local--files/test-page/valid.txt">valid.txt</a></td>
                            <td><span title="text/plain">TXT</span></td>
                            <td>100 Bytes</td>
                        </tr>
                        <tr id="file-row-101">
                            <td>No link here</td>
                            <td></td>
                            <td></td>
                        </tr>
                        <tr id="file-row-102">
                            <td>Too few columns</td>
                        </tr>
                    </tbody>
                </table>
            """
        }
        site.amc_request.return_value = [response]

        collection = PageFileCollection.acquire(page)

        assert len(collection) == 1
        assert collection[0].name == "valid.txt"


class TestPageFile:
    """PageFileのテスト"""

    def test_init(self):
        """初期化"""
        page = MagicMock()

        file = PageFile(
            page=page,
            id=123,
            name="test.txt",
            url="https://example.com/test.txt",
            mime_type="text/plain",
            size=1024,
        )

        assert file.page == page
        assert file.id == 123
        assert file.name == "test.txt"
        assert file.url == "https://example.com/test.txt"
        assert file.mime_type == "text/plain"
        assert file.size == 1024

    def test_str(self):
        """文字列表現"""
        page = MagicMock()

        file = PageFile(
            page=page,
            id=123,
            name="test.txt",
            url="https://example.com/test.txt",
            mime_type="text/plain",
            size=1024,
        )

        result = str(file)

        assert "PageFile" in result
        assert "id=123" in result
        assert "name=test.txt" in result


class TestPageFileCollectionActions:
    """PageFileCollectionの静的アクション系メソッドのテスト"""

    def test_check_exists_true(self):
        page = MagicMock()
        page.id = 1
        response = MagicMock()
        response.json.return_value = {"status": "ok", "exists": True}
        page.site.amc_request.return_value = [response]

        assert PageFileCollection.check_exists(page, "test.txt") is True
        body = page.site.amc_request.call_args[0][0][0]
        assert body["action"] == "FileAction"
        assert body["event"] == "checkFileExists"
        assert body["filename"] == "test.txt"

    def test_get_upload_form(self):
        page = MagicMock()
        page.id = 1
        response = MagicMock()
        response.json.return_value = {"status": "ok", "body": "<form></form>"}
        page.site.amc_request.return_value = [response]

        assert PageFileCollection.get_upload_form(page) == "<form></form>"

    def test_get_manager(self):
        page = MagicMock()
        page.id = 1
        response = MagicMock()
        response.json.return_value = {"status": "ok", "body": "<div>manager</div>"}
        page.site.amc_request.return_value = [response]

        assert PageFileCollection.get_manager(page) == "<div>manager</div>"

    def test_multi_upload_complete(self):
        page = MagicMock()
        page.id = 1
        response = MagicMock()
        response.json.return_value = {"status": "ok"}
        page.site.amc_request.return_value = [response]

        PageFileCollection.multi_upload_complete(page, "multikey-1", ["a.txt", "b.txt"])

        body = page.site.amc_request.call_args[0][0][0]
        assert body["action"] == "FileAction"
        assert body["event"] == "multiUploadComplete"
        assert body["multikey"] == "multikey-1"
        import json as json_module

        assert json_module.loads(body["fnames"]) == ["a.txt", "b.txt"]

    def test_upload_delegates_to_amc_client(self):
        page = MagicMock()
        page.id = 1
        page.site.unix_name = "test-site"
        page.site.ssl_supported = True
        page.site.client.amc_client.upload_file.return_value = {"status": "ok", "filename": "a.txt"}

        result = PageFileCollection.upload(page, "a.txt", b"content", multikey="mk1")

        assert result == {"status": "ok", "filename": "a.txt"}
        page.site.client.amc_client.upload_file.assert_called_once_with(
            page_id=1,
            filename="a.txt",
            content=b"content",
            site_name="test-site",
            site_ssl_supported=True,
            multikey="mk1",
        )


class TestPageFileForms:
    """PageFileのフォーム取得系メソッドのテスト"""

    def test_get_rename_form(self):
        page = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok", "body": "<form>rename</form>"}
        page.site.amc_request.return_value = [response]
        file = PageFile(page=page, id=1, name="a.txt", url="", mime_type="", size=0)

        assert file.get_rename_form() == "<form>rename</form>"

    def test_get_move_form(self):
        page = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok", "body": "<form>move</form>"}
        page.site.amc_request.return_value = [response]
        file = PageFile(page=page, id=1, name="a.txt", url="", mime_type="", size=0)

        assert file.get_move_form() == "<form>move</form>"

    def test_get_info(self):
        page = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok", "body": "<div>info</div>"}
        page.site.amc_request.return_value = [response]
        file = PageFile(page=page, id=1, name="a.txt", url="", mime_type="", size=0)

        assert file.get_info() == "<div>info</div>"


class TestPageFileRenameMoveDelete:
    """PageFile.rename / move / deleteのテスト"""

    def test_rename_success(self):
        page = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok"}
        page.site.amc_request.return_value = [response]
        file = PageFile(page=page, id=1, name="old.txt", url="", mime_type="", size=0)

        result = file.rename("new.txt")

        assert result is file
        assert file.name == "new.txt"
        body = page.site.amc_request.call_args[0][0][0]
        assert body["event"] == "renameFile"
        assert body["new_name"] == "new.txt"
        assert "force" not in body

    def test_rename_force(self):
        page = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok"}
        page.site.amc_request.return_value = [response]
        file = PageFile(page=page, id=1, name="old.txt", url="", mime_type="", size=0)

        file.rename("new.txt", force=True)

        body = page.site.amc_request.call_args[0][0][0]
        assert body["force"] == "true"

    def test_move_success(self):
        page = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok"}
        page.site.amc_request.return_value = [response]
        file = PageFile(page=page, id=1, name="a.txt", url="", mime_type="", size=0)

        file.move("other-page")

        body = page.site.amc_request.call_args[0][0][0]
        assert body["event"] == "moveFile"
        assert body["destination_page_name"] == "other-page"

    def test_delete_requires_confirm(self):
        page = MagicMock()
        file = PageFile(page=page, id=1, name="a.txt", url="", mime_type="", size=0)

        try:
            file.delete()
            raised = False
        except ValueError:
            raised = True
        assert raised is True
        page.site.amc_request.assert_not_called()

    def test_delete_with_confirm(self):
        page = MagicMock()
        response = MagicMock()
        response.json.return_value = {"status": "ok"}
        page.site.amc_request.return_value = [response]
        file = PageFile(page=page, id=1, name="a.txt", url="", mime_type="", size=0)

        file.delete(confirm=True)

        body = page.site.amc_request.call_args[0][0][0]
        assert body["action"] == "FileAction"
        assert body["event"] == "deleteFile"
        assert body["file_id"] == 1
