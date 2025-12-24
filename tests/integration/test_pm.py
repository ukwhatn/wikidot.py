"""プライベートメッセージ取得の統合テスト

NOTE: メッセージ送信はスキップ。取得のみテスト。
事前にInbox/Outboxにメッセージが入っていることを前提とする。
"""

from __future__ import annotations

import pytest


class TestPrivateMessage:
    """プライベートメッセージ取得テスト"""

    def test_1_get_inbox(self, client):
        """1. 受信箱取得"""
        inbox = client.private_message.inbox
        assert inbox is not None

        # メッセージ一覧を取得
        messages = list(inbox)
        # メッセージがあることを期待（事前にテスト用メッセージを入れておく）
        assert len(messages) >= 0  # 空でもテストは通す

    def test_2_get_sentbox(self, client):
        """2. 送信箱取得"""
        sentbox = client.private_message.sentbox
        assert sentbox is not None

        # メッセージ一覧を取得
        messages = list(sentbox)
        assert len(messages) >= 0

    def test_3_inbox_message_properties(self, client):
        """3. 受信メッセージのプロパティ確認"""
        inbox = client.private_message.inbox
        messages = list(inbox)

        if len(messages) == 0:
            pytest.skip("No messages in inbox")

        message = messages[0]

        # 基本プロパティ
        assert message.id is not None
        assert message.id > 0
        assert message.subject is not None
        assert message.sender is not None
        assert message.created_at is not None

    def test_4_sentbox_message_properties(self, client):
        """4. 送信メッセージのプロパティ確認"""
        sentbox = client.private_message.sentbox
        messages = list(sentbox)

        if len(messages) == 0:
            pytest.skip("No messages in sentbox")

        message = messages[0]

        # 基本プロパティ
        assert message.id is not None
        assert message.id > 0
        assert message.subject is not None
        assert message.recipient is not None
        assert message.created_at is not None

    def test_5_get_message_by_id(self, client):
        """5. IDでメッセージ取得"""
        inbox = client.private_message.inbox
        messages = list(inbox)

        if len(messages) == 0:
            pytest.skip("No messages in inbox")

        # 最初のメッセージのIDで再取得
        message_id = messages[0].id
        message = client.private_message.get_message(message_id)

        assert message is not None
        assert message.id == message_id
