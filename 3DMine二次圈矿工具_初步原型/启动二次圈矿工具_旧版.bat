@echo off
rem ============================================================
rem  Legacy Tkinter UI (fallback) - original client\gui.py
rem ============================================================
cd /d "%~dp0"
set "PYEXE=C:/Users/Administrator/AppData/Local/Programs/Python/Python313/python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
set "PYW=%PYEXE:python.exe=pythonw.exe%"
if exist "%PYW%" (
    start "" "%PYW%" -X utf8 "client\gui.py"
    goto :eof
)
"%PYEXE%" -X utf8 "client\gui.py"
if errorlevel 1 pause
