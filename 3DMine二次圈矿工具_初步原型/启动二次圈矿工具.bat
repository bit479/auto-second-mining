@echo off
cd /d "%~dp0"
set "PYEXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"
if not exist "%PYEXE%" (
    set "PYEXE=python"
)
rem --- GUI: prefer pythonw (same folder as python.exe), no console window ---
set "PYW=%PYEXE:python.exe=pythonw.exe%"
if exist "%PYW%" (
    start "" "%PYW%" -X utf8 "client\gui.py"
    goto :eof
)
where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw -X utf8 "client\gui.py"
    goto :eof
)
"%PYEXE%" -X utf8 "client\gui.py"
if errorlevel 1 (
    echo.
    echo FAILED: python not found or missing dependencies.
    pause
)
