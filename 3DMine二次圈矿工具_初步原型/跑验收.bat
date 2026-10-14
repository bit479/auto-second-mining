@echo off
rem ============================================================
rem  One-click acceptance (accept_all.py) - double click me
rem  1) mining gate (two tiers)  2) report spec regression
rem  3) drawing entity self-check  4) exact-mode self-check
rem  Runs full suite (~3 min) and opens ????.md when done.
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"
set "PYEXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
title Acceptance - auto second MINING
"%PYEXE%" -X utf8 "_probe\accept_all.py" --open %*
echo.
echo Exit code: %ERRORLEVEL%   (0 = all checks passed)
pause
