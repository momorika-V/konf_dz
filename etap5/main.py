r"""Транслятор учебного конфигурационного языка в TOML (вариант 22).

Этап 5 (финальный): полный синтаксис варианта 22.
- однострочные комментарии:  // текст
- многострочные комментарии: (comment текст )
- числа: \d+
- словари: $[ ИМЯ : значение, ... ]
- имена: [A-Z]+
- константы: var ИМЯ = значение;
- константные выражения (префиксная форма): |+ ИМЯ 1|
  операции: +, -, *, max(), pow()

Вход читается из файла (аргументы командной строки), результат
в формате TOML пишется в другой файл. Без аргументов программа
переходит в диалоговый режим: сама спрашивает пути и не закрывается,
пока пользователь не введёт q.

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
MIN_EXPONENT = 0  
BLOCK_OPEN = "(comment"  
BLOCK_CLOSE = ")"  
DEFAULT_OUTPUT = "out.toml"  
QUIT_CMD = "q" 
USAGE = "Запуск: python main.py <вход.cfg> <выход.toml>"

GRAMMAR = r"""
    start : statement*
    ?statement : var_decl | dict

    var_decl : "var" NAME "=" value ";"
    dict     : "$[" [ pair ("," pair)* ] "]"
    pair     : NAME ":" value
    ?value    : NUMBER | dict | expr
    expr     : "|" OP operand operand "|"
    ?operand : NUMBER | NAME | expr

    OP     : "+" | "-" | "*" | "max" | "pow"
    NAME   : /[A-Z]+/
    NUMBER : /\d+/

    LINE_COMMENT  : /\/\/[^\n]*/
    BLOCK_COMMENT : /\(comment(.|\n)*?\)/

    %ignore LINE_COMMENT
    %ignore BLOCK_COMMENT
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
    if BLOCK_OPEN in text and BLOCK_CLOSE not in text:
        return "Многострочный комментарий (comment не закрыт скобкой )"
    line, column = exc.line, exc.column
    if line is None or line < 0:  
        line = text.count("\n") + 1
        column = len(text) - text.rfind("\n")
    head = "Синтаксическая ошибка: строка {}, столбец {}.".format(
        line, column)
    return head + "\n" + exc.get_context(text).strip("\n")


def get_const(name, consts):
    """Возвращает число-константу или объясняет, чего не хватает."""
    if name not in consts:
        raise ConfigError("Константа {} не объявлена".format(name))
    value = consts[name]
    if not isinstance(value, int):
        raise ConfigError("Константа {} — не число, а словарь".format(name))
    return value


def apply_op(op, left, right):
    """Применяет операцию префиксного выражения к двум числам."""
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "max":
        return max(left, right)
    if op == "pow":
        if right < MIN_EXPONENT:
            raise ConfigError("Степень в pow не может быть отрицательной")
        return left ** right
    raise ConfigError("Неизвестная операция: " + op)


def eval_operand(node, consts):
    """Вычисляет операнд выражения: число, константу или выражение."""
    if isinstance(node, Token):
        if node.type == "NUMBER":
            return int(node)
        return get_const(node, consts)
    return eval_expr(node, consts)


def eval_expr(node, consts):
    """Вычисляет константное выражение в префиксной форме."""
    op = str(node.children[0])
    left = eval_operand(node.children[1], consts)
    right = eval_operand(node.children[2], consts)
    return apply_op(op, left, right)


def eval_value(node, consts):
    """Вычисляет значение: число, словарь или выражение."""
    if isinstance(node, Token) and node.type == "NUMBER":
        return int(node)
    if node.data == "dict":
        return build_dict(node, consts)
    return eval_expr(node, consts)


def build_dict(dict_node, consts):
    """Собирает словарь языка в обычный словарь Python."""
    result = {}
    for pair in dict_node.children:
        if pair is None: 
            continue
        name = str(pair.children[0])
        if name in result:
            raise ConfigError("Повтор имени в словаре: " + name)
        result[name] = eval_value(pair.children[1], consts)
    return result


def declare_const(node, consts):
    """Сохраняет константу из объявления var ИМЯ = значение;"""
    name = str(node.children[0])
    if name in consts:
        raise ConfigError("Константа {} объявлена дважды".format(name))
    consts[name] = eval_value(node.children[1], consts)


def run_statements(tree, consts, output):
    """Выполняет инструкции по порядку: константы и словари."""
    for statement in tree.children:
        if statement.data == "var_decl":
            declare_const(statement, consts)
        else:
            merge_dict(statement, consts, output)


def merge_dict(dict_node, consts, output):
    """Переносит пары словаря в общий результат без повторов имён."""
    part = build_dict(dict_node, consts)
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
    """Читает входной файл и объясняет любые проблемы с ним."""
    if os.path.isdir(path):
        raise ConfigError("Указана папка, а нужен файл: " + path)
    if not os.path.isfile(path):
        raise ConfigError("Входной файл не найден: " + path)
    try:
        with open(path, "r", encoding="utf-8") as source:
            return source.read()
    except UnicodeDecodeError:
        raise ConfigError("Файл не в кодировке UTF-8: " + path)


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
    consts = {}
    output = {}
    run_statements(tree, consts, output)
    return toml_text(output)


def translate_file(source_path, target_path):
    """Читает вход, транслирует его и записывает результат."""
    text = read_source(source_path)
    result = translate(text)
    write_result(target_path, result)
    print("Готово. Результат записан в файл: " + target_path)


def ask_input_path():
    """Спрашивает путь входного файла, пока не получит существующий."""
    while True:
        reply = input("Входной файл ({} — выход): ".format(QUIT_CMD))
        reply = reply.strip().strip('"')
        if reply.lower() == QUIT_CMD:
            return None
        if reply and os.path.isfile(reply):
            return reply
        print("Такого файла нет, попробуйте ещё раз.\n")


def ask_output_path():
    """Спрашивает путь результата, по умолчанию out.toml."""
    prompt = "Выходной файл [{}]: ".format(DEFAULT_OUTPUT)
    reply = input(prompt).strip().strip('"')
    return reply if reply else DEFAULT_OUTPUT


def interactive():
    """Диалоговый режим: спрашивает файлы, пока пользователь не выйдет."""
    print("Диалоговый режим: введите путь к конфигурации.\n")
    while True:
        source_path = ask_input_path()
        if source_path is None:
            return
        target_path = ask_output_path()
        try:
            translate_file(source_path, target_path)
        except ConfigError as exc:
            print("Ошибка: " + str(exc))
        print()


def main(argv):
    """Точка входа: без аргументов — диалог, с аргументами — трансляция."""
    args = argv[1:]
    if not args:
        try:
            interactive()
        except (KeyboardInterrupt, EOFError):
            print("\nРабота прервана пользователем.")
            return EXIT_ERROR
        return EXIT_OK
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
    try:
        sys.exit(main(sys.argv))
    except (KeyboardInterrupt, EOFError):
        print("\nРабота прервана пользователем.")
        sys.exit(EXIT_ERROR)
