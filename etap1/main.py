r"""Транслятор учебного конфигурационного языка в TOML (вариант 22).

Этап 1: числа и словари (включая вложенные).
Входной текст читается из файла, путь к которому задан первым
аргументом командной строки. Выходной текст в формате TOML пишется
в файл, путь к которому задан вторым аргументом.

Для разбора используется специализированный инструмент
синтаксического разбора — библиотека lark (pip install lark).
"""

import os
import sys

from lark import Lark, Token
from lark.exceptions import UnexpectedInput

EXPECTED_INPUT_COUNT = 2  
EXIT_OK = 0
EXIT_ERROR = 1
USAGE = "Запуск: python main.py <вход.cfg> <выход.toml>"

GRAMMAR = r"""
    start : dict*

    dict  : "$[" [ pair ("," pair)* ] "]"
    pair  : NAME ":" value
    ?value : NUMBER | dict

    NAME   : /[A-Z]+/
    NUMBER : /\d+/

    %ignore /[ \t\r\n]+/
"""

PARSER = Lark(GRAMMAR, parser="earley", start="start")


class ConfigError(Exception):
    """Понятная пользователю ошибка конфигурации или работы с файлами."""


def parse_text(text):
    """Разбирает текст конфигурации в дерево разбора lark."""
    try:
        return PARSER.parse(text)
    except UnexpectedInput as exc:
        raise ConfigError(syntax_message(text, exc))


def syntax_message(text, exc):
    """Собирает понятное сообщение о синтаксической ошибке."""
    line, column = exc.line, exc.column
    if line is None or line < 0:  
        line = text.count("\n") + 1
        column = len(text) - text.rfind("\n")
    head = "Синтаксическая ошибка: строка {}, столбец {}.".format(
        line, column)
    return head + "\n" + exc.get_context(text).strip("\n")


def eval_value(node):
    """Вычисляет значение: число или словарь."""
    if isinstance(node, Token) and node.type == "NUMBER":
        return int(node)
    return build_dict(node)


def build_dict(dict_node):
    """Собирает словарь языка в обычный словарь Python."""
    result = {}
    for pair in dict_node.children:
        if pair is None:  
            continue
        name = str(pair.children[0])
        if name in result:
            raise ConfigError("Повтор имени в словаре: " + name)
        result[name] = eval_value(pair.children[1])
    return result


def run_statements(tree, output):
    """Переносит пары всех словарей в общий результат."""
    for dict_node in tree.children:
        part = build_dict(dict_node)
        for name, value in part.items():
            if name in output:
                raise ConfigError("Повтор имени: " + name)
            output[name] = value


def toml_lines(table, prefix):
    """Строит строки TOML: простые значения, затем вложенные таблицы."""
    lines = []
    subtables = []
    for key, value in table.items():
        if isinstance(value, dict):
            subtables.append((key, value))
        else:
            lines.append("{} = {}".format(key, value))
    for key, value in subtables:
        lines.append("[{}]".format(prefix + key))
        lines.extend(toml_lines(value, prefix + key + "."))
    return lines


def toml_text(table):
    """Собирает итоговый текст TOML с переводом строки в конце."""
    body = "\n".join(toml_lines(table, ""))
    if body:
        return body + "\n"
    return ""


def read_source(path):
    """Читает входной файл и объясняет проблему, если файла нет."""
    if not os.path.isfile(path):
        raise ConfigError("Входной файл не найден: " + path)
    with open(path, "r", encoding="utf-8") as source:
        return source.read()


def write_result(path, text):
    """Записывает TOML в файл и объясняет проблему, если не вышло."""
    try:
        with open(path, "w", encoding="utf-8") as target:
            target.write(text)
    except OSError:
        raise ConfigError("Нельзя записать файл: " + path)


def translate(text):
    """Превращает текст конфигурации в готовый текст TOML."""
    tree = parse_text(text)
    output = {}
    run_statements(tree, output)
    return toml_text(output)


def translate_file(source_path, target_path):
    """Читает вход, транслирует его и записывает результат."""
    text = read_source(source_path)
    result = translate(text)
    write_result(target_path, result)
    print("Готово. Результат записан в файл: " + target_path)


def main(argv):
    """Точка входа: проверяет аргументы и запускает трансляцию."""
    args = argv[1:]
    if len(args) != EXPECTED_INPUT_COUNT:
        print(USAGE)
        return EXIT_ERROR
    try:
        translate_file(args[0], args[1])
    except ConfigError as exc:
        print("Ошибка: " + str(exc))
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
