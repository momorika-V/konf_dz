#!/bin/sh
# Запуск: ./run.sh вход.cfg [выход.toml]; тесты: ./run.sh test
cd "$(dirname "$0")"
if [ "$1" = "test" ]; then
    if command -v python3 >/dev/null 2>&1; then
        python3 -m unittest test_main -v
    else
        python -m unittest test_main -v
    fi
elif command -v python3 >/dev/null 2>&1; then
    python3 main.py "$@"
else
    python main.py "$@"
fi
