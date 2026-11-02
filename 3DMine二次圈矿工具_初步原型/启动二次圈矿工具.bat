@echo off
rem ============================================================
rem  Default launcher: new UI (PySide6), automatic fallback to
rem  the legacy Tkinter UI when PySide6 is missing or new UI fails.
rem  Keep this file pure ASCII (cmd.exe parses .bat as GBK).
rem ============================================================
cd /d "%~dp0"
set "PYEXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

"%PYEXE%" -c "import PySide6" >nul 2>nul
if errorlevel 1 goto legacy

set "PYW=%PYEXE:python.exe=pythonw.exe%"
if exist "%PYW%" (
    start "" "%PYW%" -X utf8 "client\ui_v2\app.py"
    goto :eof
)
"%PYEXE%" -X utf8 "client\ui_v2\app.py"
if not errorlevel 1 goto :eof
echo.
echo  [WARN] new UI exited with an error - starting the legacy UI ...

:legacy
echo.
echo  Using the legacy Tkinter UI.
echo  To use the new workbench:  "%PYEXE%" -m pip install PySide6
echo.
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
