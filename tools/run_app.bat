@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
 echo Missing development environment. See docs\DEVELOPMENT.md.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" "src\main.py" %*
if errorlevel 1 pause
