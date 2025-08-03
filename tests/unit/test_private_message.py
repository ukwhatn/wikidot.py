"""Tests for PrivateMessage refactoring."""

import unittest
from unittest.mock import Mock, patch

from wikidot.module.private_message import PrivateMessageCollection, PrivateMessageInbox, PrivateMessageSentBox


class TestPrivateMessageRefactoring(unittest.TestCase):
    """Test the refactored PrivateMessage factory methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        # Create an actual PrivateMessageCollection instead of a mock since the classes inherit from it
        self.mock_collection = PrivateMessageCollection()
        self.message_ids = [1, 2, 3]

    @patch.object(PrivateMessageCollection, "from_ids")
    def test_inbox_factory_from_ids(self, mock_from_ids):
        """Test PrivateMessageInbox._factory_from_ids method."""
        mock_from_ids.return_value = self.mock_collection

        result = PrivateMessageInbox._factory_from_ids(self.mock_client, self.message_ids)

        mock_from_ids.assert_called_once_with(self.mock_client, self.message_ids)
        self.assertIsInstance(result, PrivateMessageInbox)

    @patch.object(PrivateMessageCollection, "_acquire")
    def test_inbox_factory_acquire(self, mock_acquire):
        """Test PrivateMessageInbox._factory_acquire method."""
        mock_acquire.return_value = self.mock_collection
        module_name = "dashboard/messages/DMInboxModule"

        result = PrivateMessageInbox._factory_acquire(self.mock_client, module_name)

        mock_acquire.assert_called_once_with(self.mock_client, module_name)
        self.assertIsInstance(result, PrivateMessageInbox)

    @patch.object(PrivateMessageInbox, "_factory_from_ids")
    def test_inbox_from_ids_uses_factory(self, mock_factory):
        """Test that PrivateMessageInbox.from_ids uses the factory method."""
        mock_factory.return_value = Mock(spec=PrivateMessageInbox)

        result = PrivateMessageInbox.from_ids(self.mock_client, self.message_ids)

        mock_factory.assert_called_once_with(self.mock_client, self.message_ids)

    @patch.object(PrivateMessageInbox, "_factory_acquire")
    def test_inbox_acquire_uses_factory(self, mock_factory):
        """Test that PrivateMessageInbox.acquire uses the factory method."""
        mock_factory.return_value = Mock(spec=PrivateMessageInbox)

        result = PrivateMessageInbox.acquire(self.mock_client)

        mock_factory.assert_called_once_with(self.mock_client, "dashboard/messages/DMInboxModule")

    @patch.object(PrivateMessageCollection, "from_ids")
    def test_sentbox_factory_from_ids(self, mock_from_ids):
        """Test PrivateMessageSentBox._factory_from_ids method."""
        mock_from_ids.return_value = self.mock_collection

        result = PrivateMessageSentBox._factory_from_ids(self.mock_client, self.message_ids)

        mock_from_ids.assert_called_once_with(self.mock_client, self.message_ids)
        self.assertIsInstance(result, PrivateMessageSentBox)

    @patch.object(PrivateMessageCollection, "_acquire")
    def test_sentbox_factory_acquire(self, mock_acquire):
        """Test PrivateMessageSentBox._factory_acquire method."""
        mock_acquire.return_value = self.mock_collection
        module_name = "dashboard/messages/DMSentModule"

        result = PrivateMessageSentBox._factory_acquire(self.mock_client, module_name)

        mock_acquire.assert_called_once_with(self.mock_client, module_name)
        self.assertIsInstance(result, PrivateMessageSentBox)

    @patch.object(PrivateMessageSentBox, "_factory_from_ids")
    def test_sentbox_from_ids_uses_factory(self, mock_factory):
        """Test that PrivateMessageSentBox.from_ids uses the factory method."""
        mock_factory.return_value = Mock(spec=PrivateMessageSentBox)

        result = PrivateMessageSentBox.from_ids(self.mock_client, self.message_ids)

        mock_factory.assert_called_once_with(self.mock_client, self.message_ids)

    @patch.object(PrivateMessageSentBox, "_factory_acquire")
    def test_sentbox_acquire_uses_factory(self, mock_factory):
        """Test that PrivateMessageSentBox.acquire uses the factory method."""
        mock_factory.return_value = Mock(spec=PrivateMessageSentBox)

        result = PrivateMessageSentBox.acquire(self.mock_client)

        mock_factory.assert_called_once_with(self.mock_client, "dashboard/messages/DMSentModule")


if __name__ == "__main__":
    unittest.main()