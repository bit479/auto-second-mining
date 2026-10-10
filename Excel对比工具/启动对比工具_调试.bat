@echo off
setlocal
cd /d "%~dp0"

set "PY="
set "PYW="

REM --- 1) PATH ---
for %%X in (pythonw python py) do (
    if not defined PYW if not defined PY (
        where %%X >nul 2>nul && (
            %%X -c "import tkinter,openpyxl" >nul 2>nul && (
                if /i "%%X"=="pythonw" (set "PYW=%%X") else (set "PY=%%X")
            )
        )
    )
)

REM --- 2) 探测安装目录 ---
if not defined PYW if not defined PY (
    call :probe "%LOCALAPPDATA%\Programs\Python\Python313"
    call :probe "%LOCALAPPDATA%\Programs\Python\Python312"
    call :probe "C:\Program Files\Python313"
)

if not defined PYW if not defined PY (
    echo 未找到带 tkinter 和 openpyxl 的 Python。
    pause
    exit /b 1
)

REM 调试版: 尽量用控制台 python(崩溃时能看到红色报错)
if not defined PY if defined PYW (
    set "PY=%PYW:pythonw.exe=python.exe%"
    if not exist "%PY%" set "PY="
)
if defined PY (
    echo 使用: %PY%
    echo (崩溃时下方会显示红色报错; 按任意键可关闭此窗口)
    cmd /c ""%PY%" -X utf8 "%~dp0gui.py""
) else (
    echo 使用(无控制台): %PYW% ，错误将写入 gui_error.log
    cmd /c ""%PYW%" -X utf8 "%~dp0gui.py" 2> "%~dp0gui_error.log""
)
echo.
echo 程序已退出，按任意键关闭此窗口。
pause
endlocal
goto :eof

:probe
if defined PYW goto :eof
if defined PY goto :eof
if exist "%~1\pythonw.exe" (
    "%~1\pythonw.exe" -c "import tkinter,openpyxl" >nul 2>nul && set "PYW=%~1\pythonw.exe" && goto :eof
)
if exist "%~1\python.exe" (
    "%~1\python.exe" -c "import tkinter,openpyxl" >nul 2>nul && set "PY=%~1\python.exe"
)
goto :eof
