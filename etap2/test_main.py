"""Тесты этапа 2: этап 1 плюс однострочные и многострочные комментарии."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main


class TranslateTest(unittest.TestCase):
    """Проверки трансляции словарей в TOML."""

    def test_single_number(self):
        self.assertEqual(main.translate("$[PORT: 80]"), "PORT = 80\n")

    def test_several_pairs(self):
        text = "$[PORT: 80, TIMEOUT: 30]"
        expected = "PORT = 80\nTIMEOUT = 30\n"
        self.assertEqual(main.translate(text), expected)

    def test_several_top_dicts(self):
        text = "$[PORT: 80]\n$[TIMEOUT: 30]"
        expected = "PORT = 80\nTIMEOUT = 30\n"
        self.assertEqual(main.translate(text), expected)

    def test_nested_dict(self):
        text = "$[SERVER: $[PORT: 80]]"
        self.assertEqual(main.translate(text), "[SERVER]\nPORT = 80\n")

    def test_deep_nesting(self):
        text = "$[A: $[B: $[C: 1]]]"
        expected = "[A]\n[A.B]\nC = 1\n"
        self.assertEqual(main.translate(text), expected)

    def test_empty_dict(self):
        self.assertEqual(main.translate("$[]"), "")

    def test_duplicate_name_in_dict(self):
        with self.assertRaises(main.ConfigError):
            main.translate("$[A: 1, A: 2]")

    def test_duplicate_name_across_dicts(self):
        text = "$[A: 1]\n$[A: 2]"
        with self.assertRaises(main.ConfigError):
            main.translate(text)

    def test_missing_colon(self):
        with self.assertRaises(main.ConfigError):
            main.translate("$[PORT 80]")

    def test_missing_bracket(self):
        with self.assertRaises(main.ConfigError):
            main.translate("$[PORT: 80")

    def test_lowercase_name(self):
        with self.assertRaises(main.ConfigError):
            main.translate("$[port: 80]")


class CommentTest(unittest.TestCase):
    """Проверки однострочных и многострочных комментариев."""

    def test_line_comment(self):
        text = "// привет\n$[PORT: 80]"
        self.assertEqual(main.translate(text), "PORT = 80\n")

    def test_line_comment_at_end(self):
        text = "$[PORT: 80] // комментарий в конце"
        self.assertEqual(main.translate(text), "PORT = 80\n")

    def test_line_comment_inside_dict(self):
        text = "$[\n  // порт сервера\n  PORT: 80\n]"
        self.assertEqual(main.translate(text), "PORT = 80\n")

    def test_line_comment_between_pairs(self):
        text = "$[\n  PORT: 80, // порт\n  TIMEOUT: 30\n]"
        expected = "PORT = 80\nTIMEOUT = 30\n"
        self.assertEqual(main.translate(text), expected)

    def test_block_comment(self):
        text = "(comment\nэто комментарий\n)\n$[PORT: 80]"
        self.assertEqual(main.translate(text), "PORT = 80\n")

    def test_block_comment_inside_dict(self):
        text = "$[\n(comment\nстрока 1\nстрока 2\n)\nPORT: 80\n]"
        self.assertEqual(main.translate(text), "PORT = 80\n")

    def test_unterminated_block_comment(self):
        text = "$[PORT: 80]\n(comment забыли закрыть"
        with self.assertRaises(main.ConfigError):
            main.translate(text)


if __name__ == "__main__":
    unittest.main()
