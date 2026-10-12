@echo off
cd /d "%~dp0"

REM Console Python for debugging (shows crash traceback on screen).
set "PY=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"

if not exist "%PY%" goto :notfound

"%PY%" -X utf8 "%~dp0gui.py"
echo.
echo Program exited. Press any key to close.
pause
goto :eof

:notfound
echo.
echo [ERROR] Python interpreter not found at:
echo   %PY%
echo.
echo Please install official Python 3.13 (tick "Add to PATH").
echo.
pause
