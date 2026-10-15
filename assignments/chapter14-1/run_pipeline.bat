@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [FAIL] .venv\Scripts\python.exe not found. Create venv first.
    exit /b 1
)
".venv\Scripts\python.exe" "run_pipeline.py"
exit /b %errorlevel%
