@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

rem --- Locate a usable Python interpreter (ASCII only: cmd parses .bat as GBK) ---
set "PYEXE="
python -c "import sys" >nul 2>nul && set "PYEXE=python"
if not defined PYEXE py -c "import sys" >nul 2>nul && set "PYEXE=py"
if not defined PYEXE python3 -c "import sys" >nul 2>nul && set "PYEXE=python3"
if not defined PYEXE (
  echo [ERROR] Python not found.
  echo Please install Python 3.10 or newer, and tick "Add to PATH" during setup.
  pause
  exit /b 1
)

rem --- Dependency check / auto install (messages come from Python, UTF-8 safe) ---
%PYEXE% "%~dp0bootstrap.py"
if errorlevel 1 (
  pause
  exit /b 1
)

rem --- GUI without a console window in the taskbar; CLI keeps the console ---
if not "%~1"=="" goto :cli
pythonw -c "import openpyxl" >nul 2>nul
if errorlevel 1 (
  %PYEXE% "%~dp0main.py" --gui
  if errorlevel 1 pause
  goto :eof
)
pythonw "%~dp0main.py" --gui
goto :eof

:cli
%PYEXE% "%~dp0main.py" %*
if errorlevel 1 pause
goto :eof
