"""Tests for QuickModule refactoring."""

import unittest
from unittest.mock import Mock, patch

from wikidot.util.quick_module import QMCPage, QMCUser, QuickModule


class TestQuickModuleRefactoring(unittest.TestCase):
    """Test the refactored QuickModule generic lookup functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_response = {
            "users": [
                {"user_id": "123", "name": "test_user_1"},
                {"user_id": "456", "name": "test_user_2"},
            ],
            "pages": [
                {"title": "Test Page", "unix_name": "test-page"},
                {"title": "Another Page", "unix_name": "another-page"},
            ],
        }

    @patch.object(QuickModule, "_request")
    def test_generic_lookup_with_users(self, mock_request):
        """Test the generic lookup method with user data."""
        mock_request.return_value = {"users": self.mock_response["users"]}

        result = QuickModule._generic_lookup(
            "TestModule",
            123,
            "test_query",
            "users",
            QMCUser,
            lambda cls, item: cls(id=int(item["user_id"]), name=item["name"]),
        )

        # Verify the request was called correctly
        mock_request.assert_called_once_with("TestModule", 123, "test_query")

        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], QMCUser)
        self.assertEqual(result[0].id, 123)
        self.assertEqual(result[0].name, "test_user_1")
        self.assertEqual(result[1].id, 456)
        self.assertEqual(result[1].name, "test_user_2")

    @patch.object(QuickModule, "_request")
    def test_generic_lookup_with_false_response(self, mock_request):
        """Test the generic lookup method handles False response (member_lookup case)."""
        mock_request.return_value = {"users": False}

        result = QuickModule._generic_lookup(
            "MemberLookupQModule",
            123,
            "test_query",
            "users",
            QMCUser,
            lambda cls, item: cls(id=int(item["user_id"]), name=item["name"]),
        )

        # Should return empty list when response is False
        self.assertEqual(result, [])

    @patch.object(QuickModule, "_generic_lookup")
    def test_member_lookup_uses_generic(self, mock_generic):
        """Test that member_lookup uses the generic lookup method."""
        mock_generic.return_value = [QMCUser(id=123, name="test_user")]

        result = QuickModule.member_lookup(123, "test_query")

        mock_generic.assert_called_once_with(
            "MemberLookupQModule",
            123,
            "test_query",
            "users",
            QMCUser,
            unittest.mock.ANY,  # The lambda function
        )
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], QMCUser)

    @patch.object(QuickModule, "_generic_lookup")
    def test_user_lookup_uses_generic(self, mock_generic):
        """Test that user_lookup uses the generic lookup method."""
        mock_generic.return_value = [QMCUser(id=456, name="test_user")]

        result = QuickModule.user_lookup(456, "test_query")

        mock_generic.assert_called_once_with(
            "UserLookupQModule",
            456,
            "test_query",
            "users",
            QMCUser,
            unittest.mock.ANY,  # The lambda function
        )
        self.assertEqual(len(result), 1)

    @patch.object(QuickModule, "_generic_lookup")
    def test_page_lookup_uses_generic(self, mock_generic):
        """Test that page_lookup uses the generic lookup method."""
        mock_generic.return_value = [QMCPage(title="Test Page", unix_name="test-page")]

        result = QuickModule.page_lookup(789, "test_query")

        mock_generic.assert_called_once_with(
            "PageLookupQModule",
            789,
            "test_query",
            "pages",
            QMCPage,
            unittest.mock.ANY,  # The lambda function
        )
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], QMCPage)


if __name__ == "__main__":
    unittest.main()