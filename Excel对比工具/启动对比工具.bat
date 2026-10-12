@echo off
cd /d "%~dp0"

REM Known-good system Python on this machine (verified). No env probing.
set "PY=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\pythonw.exe"

if not exist "%PY%" goto :notfound

start "ExcelDiff" "%PY%" -X utf8 "%~dp0gui.py"
goto :eof

:notfound
echo.
echo [ERROR] Python interpreter not found at:
echo   %PY%
echo.
echo Please install official Python 3.13 (tick "Add to PATH"), or run the
echo debug bat: 启动对比工具_调试.bat
echo.
pause
