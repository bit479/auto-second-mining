@echo off
rem ============================================================
rem  First-run / new-machine environment self check
rem  (Python version, packages, data folders, params, output dir,
rem   AutoCAD availability) - double click me.
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"
set "PYEXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
title Preflight check - auto second MINING
"%PYEXE%" -X utf8 "core\preflight.py"
echo.
echo Exit code: %ERRORLEVEL%   (0 = ready to use)
pause
