"""Тесты этапа 1: числа, словари, вложенность и простые ошибки."""

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

    def test_empty_input(self):
        self.assertEqual(main.translate(""), "")

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

    def test_unknown_character(self):
        with self.assertRaises(main.ConfigError):
            main.translate("$[PORT: восемь]")


if __name__ == "__main__":
    unittest.main()
