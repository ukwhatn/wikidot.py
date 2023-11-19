import unittest
from wikidot.util import convert_string
from wikidot.util.table import char_table


class ToUnixTestCase(unittest.TestCase):
    def test_special_alphabet(self):
        """Test special alphabet conversion."""
        for key, value in char_table.special_char_map.items():
            self.assertEqual(convert_string.to_unix(key), value)

    def test_lowercase(self):
        """Test lowercase conversion."""
        self.assertEqual(convert_string.to_unix('ABC'), 'abc')

    def test_ascii(self):
        """Test ascii conversion."""
        self.assertEqual(convert_string.to_unix('abc123'), 'abc123')
        self.assertEqual(convert_string.to_unix('abc!@#'), 'abc')
        self.assertEqual(convert_string.to_unix('abcあいう'), 'abc')

    def test_remove_colon(self):
        """Test colon removal."""
        self.assertEqual(convert_string.to_unix(':test'), 'test')
        self.assertEqual(convert_string.to_unix('test:'), 'test')
        self.assertEqual(convert_string.to_unix(':test:'), 'test')
        self.assertEqual(convert_string.to_unix('test:test'), 'test:test')


if __name__ == '__main__':
    unittest.main()
