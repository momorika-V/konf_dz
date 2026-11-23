"""Тесты этапа 4: всё из этапа 3 плюс константные выражения."""

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

    def test_const_redeclare(self):
        text = "var A = 1;\nvar A = 2;"
        with self.assertRaises(main.ConfigError):
            main.translate(text)

    def test_const_without_semicolon(self):
        text = "var A = 1\n$[]"
        with self.assertRaises(main.ConfigError):
            main.translate(text)


class ExprTest(unittest.TestCase):
    """Проверки константных выражений в префиксной форме."""

    def test_add(self):
        self.assertEqual(main.translate("$[A: |+ 1 2|]"), "A = 3\n")

    def test_sub(self):
        self.assertEqual(main.translate("$[A: |- 5 8|]"), "A = -3\n")

    def test_mul(self):
        self.assertEqual(main.translate("$[A: |* 6 7|]"), "A = 42\n")

    def test_max(self):
        self.assertEqual(main.translate("$[A: |max 3 9|]"), "A = 9\n")

    def test_pow(self):
        self.assertEqual(main.translate("$[A: |pow 2 10|]"), "A = 1024\n")

    def test_expr_in_nested_dict(self):
        text = "$[S: $[PORT: |+ 8000 80|]]"
        expected = "[S]\nPORT = 8080\n"
        self.assertEqual(main.translate(text), expected)

    def test_const_in_expr(self):
        text = "var BASE = 8000;\n$[PORT: |+ BASE 80|]"
        self.assertEqual(main.translate(text), "PORT = 8080\n")

    def test_nested_expr(self):
        text = "$[A: |+ |* 2 3| 1|]"
        self.assertEqual(main.translate(text), "A = 7\n")

    def test_expr_in_var_value(self):
        text = "var X = |+ 2 2|;\n$[A: |* X 2|]"
        self.assertEqual(main.translate(text), "A = 8\n")

    def test_bare_name_is_error(self):
        text = "var X = 5;\n$[A: X]"
        with self.assertRaises(main.ConfigError):
            main.translate(text)

    def test_undeclared_const(self):
        with self.assertRaises(main.ConfigError):
            main.translate("$[A: |+ NOPE 1|]")

    def test_const_used_before_declaration(self):
        text = "$[A: |+ X 1|]\nvar X = 5;"
        with self.assertRaises(main.ConfigError):
            main.translate(text)

    def test_dict_const_in_expr(self):
        text = "var D = $[A: 1];\n$[B: |+ D 1|]"
        with self.assertRaises(main.ConfigError):
            main.translate(text)

    def test_negative_pow(self):
        text = "$[A: |pow 2 |- 1 2||]"
        with self.assertRaises(main.ConfigError):
            main.translate(text)

    def test_expr_without_operands(self):
        with self.assertRaises(main.ConfigError):
            main.translate("$[A: |+ 1|]")


if __name__ == "__main__":
    unittest.main()
