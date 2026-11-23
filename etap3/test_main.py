"""Тесты этапа 3: этап 2 плюс объявление констант var."""

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

    def test_line_comment_inside_dict(self):
        text = "$[\n  // порт сервера\n  PORT: 80\n]"
        self.assertEqual(main.translate(text), "PORT = 80\n")

    def test_block_comment(self):
        text = "(comment\nэто комментарий\n)\n$[PORT: 80]"
        self.assertEqual(main.translate(text), "PORT = 80\n")

    def test_unterminated_block_comment(self):
        text = "$[PORT: 80]\n(comment забыли закрыть"
        with self.assertRaises(main.ConfigError):
            main.translate(text)


class ConstTest(unittest.TestCase):
    """Проверки объявления констант var ИМЯ = значение;"""

    def test_const_number(self):
        text = "var SIZE = 10;\n$[PORT: 80]"
        self.assertEqual(main.translate(text), "PORT = 80\n")

    def test_const_not_in_output(self):
        text = "var SIZE = 10;\n$[]"
        self.assertEqual(main.translate(text), "")

    def test_const_dict(self):
        text = "var OPTS = $[LEVEL: 2];\n$[]"
        self.assertEqual(main.translate(text), "")

    def test_const_with_comment(self):
        text = "// базовый порт\nvar BASE = 8000;\n$[PORT: 80]"
        self.assertEqual(main.translate(text), "PORT = 80\n")

    def test_const_redeclare(self):
        text = "var A = 1;\nvar A = 2;"
        with self.assertRaises(main.ConfigError):
            main.translate(text)

    def test_const_without_semicolon(self):
        text = "var A = 1\n$[]"
        with self.assertRaises(main.ConfigError):
            main.translate(text)

    def test_const_lowercase_name(self):
        text = "var base = 1;"
        with self.assertRaises(main.ConfigError):
            main.translate(text)


if __name__ == "__main__":
    unittest.main()
