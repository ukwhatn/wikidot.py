"""Tests for PageRevisionCollection refactoring."""

import unittest
from unittest.mock import Mock, patch

from wikidot.module.page_revision import PageRevisionCollection


class TestPageRevisionRefactoring(unittest.TestCase):
    """Test the refactored PageRevisionCollection generic acquire functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_page = Mock()
        self.mock_page.site.amc_request = Mock()
        
        # Mock revisions
        self.mock_revision1 = Mock()
        self.mock_revision1.id = 1
        self.mock_revision1.is_source_acquired.return_value = False
        self.mock_revision1.is_html_acquired.return_value = False
        
        self.mock_revision2 = Mock()
        self.mock_revision2.id = 2
        self.mock_revision2.is_source_acquired.return_value = True  # Already acquired
        self.mock_revision2.is_html_acquired.return_value = False
        
        self.revisions = [self.mock_revision1, self.mock_revision2]

    def test_generic_acquire_filters_already_acquired(self):
        """Test that _generic_acquire filters out already acquired revisions."""
        check_func = Mock(side_effect=[False, True])  # First not acquired, second acquired
        process_func = Mock()
        
        # Mock the amc_request response
        mock_response = Mock()
        mock_response.json.return_value = {"body": "test_body"}
        self.mock_page.site.amc_request.return_value = [mock_response]

        result = PageRevisionCollection._generic_acquire(
            self.mock_page,
            self.revisions,
            check_func,
            "test/Module",
            process_func
        )

        # Should only process the first revision (not acquired)
        self.mock_page.site.amc_request.assert_called_once_with([
            {"moduleName": "test/Module", "revision_id": 1}
        ])
        process_func.assert_called_once_with(self.mock_revision1, mock_response, self.mock_page)
        self.assertEqual(result, self.revisions)

    def test_generic_acquire_returns_early_if_all_acquired(self):
        """Test that _generic_acquire returns early if all revisions are already acquired."""
        check_func = Mock(return_value=True)  # All already acquired
        process_func = Mock()

        result = PageRevisionCollection._generic_acquire(
            self.mock_page,
            self.revisions,
            check_func,
            "test/Module",
            process_func
        )

        # Should not make any requests
        self.mock_page.site.amc_request.assert_not_called()
        process_func.assert_not_called()
        self.assertEqual(result, self.revisions)

    @patch.object(PageRevisionCollection, "_generic_acquire")
    def test_acquire_sources_uses_generic(self, mock_generic):
        """Test that _acquire_sources uses the generic acquire method."""
        mock_generic.return_value = self.revisions

        result = PageRevisionCollection._acquire_sources(self.mock_page, self.revisions)

        # Verify _generic_acquire was called with correct parameters
        self.assertEqual(mock_generic.call_count, 1)
        call_args = mock_generic.call_args[0]
        
        self.assertEqual(call_args[0], self.mock_page)
        self.assertEqual(call_args[1], self.revisions)
        self.assertEqual(call_args[3], "history/PageSourceModule")
        
        # The check function should be a lambda that calls is_source_acquired
        check_func = call_args[2]
        test_revision = Mock()
        test_revision.is_source_acquired.return_value = True
        self.assertTrue(check_func(test_revision))

    @patch.object(PageRevisionCollection, "_generic_acquire")
    def test_acquire_htmls_uses_generic(self, mock_generic):
        """Test that _acquire_htmls uses the generic acquire method."""
        mock_generic.return_value = self.revisions

        result = PageRevisionCollection._acquire_htmls(self.mock_page, self.revisions)

        # Verify _generic_acquire was called with correct parameters
        self.assertEqual(mock_generic.call_count, 1)
        call_args = mock_generic.call_args[0]
        
        self.assertEqual(call_args[0], self.mock_page)
        self.assertEqual(call_args[1], self.revisions)
        self.assertEqual(call_args[3], "history/PageVersionModule")
        
        # The check function should be a lambda that calls is_html_acquired
        check_func = call_args[2]
        test_revision = Mock()
        test_revision.is_html_acquired.return_value = True
        self.assertTrue(check_func(test_revision))

    @patch.object(PageRevisionCollection, "_acquire_sources")
    def test_get_sources_delegates_to_acquire_sources(self, mock_acquire):
        """Test that get_sources delegates to _acquire_sources."""
        collection = PageRevisionCollection()
        collection.page = self.mock_page
        collection.extend(self.revisions)
        
        mock_acquire.return_value = collection

        result = collection.get_sources()

        mock_acquire.assert_called_once_with(self.mock_page, collection)
        self.assertEqual(result, collection)

    @patch.object(PageRevisionCollection, "_acquire_htmls")
    def test_get_htmls_delegates_to_acquire_htmls(self, mock_acquire):
        """Test that get_htmls delegates to _acquire_htmls."""
        collection = PageRevisionCollection()
        collection.page = self.mock_page
        collection.extend(self.revisions)
        
        mock_acquire.return_value = collection

        result = collection.get_htmls()

        mock_acquire.assert_called_once_with(self.mock_page, collection)
        self.assertEqual(result, collection)


if __name__ == "__main__":
    unittest.main()