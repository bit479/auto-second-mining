@echo off
rem ============================================================
rem  New UI launcher (PySide6) : Geological Mining Workspace
rem  NOTE: keep this file pure ASCII (cmd.exe parses .bat as GBK)
rem ============================================================
cd /d "%~dp0"
set "PYEXE=C:/Users/Administrator/AppData/Local/Programs/Python/Python313/python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

"%PYEXE%" -c "import PySide6" >nul 2>nul
if errorlevel 1 (
    echo.
    echo  [ERROR] PySide6 not installed for: %PYEXE%
    echo  Fix:  "%PYEXE%" -m pip install PySide6
    echo  Or use the legacy Tkinter launcher BAT in this folder.
    echo.
    pause
    exit /b 1
)

set "PYW=%PYEXE:python.exe=pythonw.exe%"
if exist "%PYW%" (
    start "" "%PYW%" -X utf8 "client\ui_v2\app.py"
    goto :eof
)
"%PYEXE%" -X utf8 "client\ui_v2\app.py"
if errorlevel 1 pause
