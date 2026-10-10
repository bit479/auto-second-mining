@echo off
setlocal
cd /d "%~dp0"

set "PY="
set "PYW="

REM Step 1: try py launcher / pythonw / python from PATH
where py >nul 2>nul
if not errorlevel 1 (
    py -c "import tkinter,openpyxl" >nul 2>nul
    if not errorlevel 1 ( set "PY=py" & goto :launch )
)
where pythonw >nul 2>nul
if not errorlevel 1 (
    pythonw -c "import tkinter,openpyxl" >nul 2>nul
    if not errorlevel 1 ( set "PYW=pythonw" & goto :launch )
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import tkinter,openpyxl" >nul 2>nul
    if not errorlevel 1 ( set "PY=python" & goto :launch )
)

REM Step 2: probe common install dirs (works even if Python is not in PATH)
call :probe "%LOCALAPPDATA%\Programs\Python\Python313"
call :probe "%LOCALAPPDATA%\Programs\Python\Python312"
call :probe "%LOCALAPPDATA%\Programs\Python\Python311"
call :probe "%LOCALAPPDATA%\Programs\Python\Python310"
call :probe "C:\Program Files\Python313"
call :probe "C:\Program Files\Python312"
call :probe "C:\Program Files\Python311"
call :probe "C:\Program Files\Python310"
call :probe "C:\Python313"
call :probe "C:\Python312"
call :probe "C:\Python311"

:launch
if defined PYW (
    start "" "%PYW%" -X utf8 "%~dp0gui.py"
    goto :done
)
if defined PY (
    start "" "%PY" -X utf8 "%~dp0gui.py"
    goto :done
)

echo.
echo ERROR: Python with tkinter and openpyxl was not found on this machine.
echo Please install official Python from https://www.python.org
echo (tick "Add python.exe to PATH" during install), then run:
echo   pip install openpyxl
echo.
pause
goto :done

:probe
if defined PYW goto :eof
if defined PY goto :eof
if exist "%~1\pythonw.exe" (
    "%~1\pythonw.exe" -c "import tkinter,openpyxl" >nul 2>nul
    if not errorlevel 1 ( set "PYW=%~1\pythonw.exe" & goto :eof )
)
if exist "%~1\python.exe" (
    "%~1\python.exe" -c "import tkinter,openpyxl" >nul 2>nul
    if not errorlevel 1 ( set "PY=%~1\python.exe" )
)
goto :eof

:done
endlocal
