@echo off
chcp 65001 >nul
cd /d %~dp0
if "%~1"=="test" (
    python -m unittest test_main -v
) else (
    python main.py %*
)
pause
