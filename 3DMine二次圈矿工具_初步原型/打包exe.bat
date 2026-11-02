@echo off
rem ============================================================
rem  Build single-file exe (needs PySide6 + PyInstaller + deps)
rem  Edit BUILD_PY if your build venv lives elsewhere.
rem ============================================================
cd /d "%~dp0"
set "BUILD_PY=E:/AAAWK/NNN CRT\_buildenv\venv2\Scripts\python.exe"
if not exist "%BUILD_PY%" (
    echo  [ERROR] build python not found: %BUILD_PY%
    echo  Create one:  python -m venv <dir>  then  pip install PySide6 numpy scipy shapely matplotlib ezdxf openpyxl xlrd xlwt xlutils pyodbc pillow pyinstaller
    pause
    exit /b 1
)
"%BUILD_PY%" -X utf8 "_probe\build_exe.py" %*
if errorlevel 1 pause
