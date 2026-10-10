@echo off
setlocal
set "CHOSEN="
for %%X in (pythonw python py python3) do (
    if not defined CHOSEN (
        where %%X >nul 2>nul && %%X -c "import tkinter,openpyxl" >nul 2>nul && set "CHOSEN=%%X"
    )
)
if not defined CHOSEN (
    echo Python with tkinter and openpyxl not found.
    echo Please install official Python and run: pip install openpyxl
    pause
    exit /b 1
)
start "" "%CHOSEN%" -X utf8 "%~dp0gui.py"
endlocal
