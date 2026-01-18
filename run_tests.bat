@echo off
chcp 65001 >nul
set PYTHONPATH=%~dp0
pytest -vv
pause
