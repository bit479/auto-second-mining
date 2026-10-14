@echo off
rem ============================================================
rem  Parameter ledger (params_report.py) - double click me
rem  Shows: global defaults -> platform overrides -> blast overrides,
rem  with the reason (_??) for every override.  ? = no reason given.
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"
set "PYEXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
title Parameter ledger - auto second MINING
"%PYEXE%" -X utf8 "_probe\params_report.py"
echo.
echo (Want only one platform? Run:  python _probe\params_report.py 3960)
pause
