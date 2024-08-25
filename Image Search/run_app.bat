@echo off
echo Starting Image Search App...

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Run the Python script
python main.py
if %errorlevel% neq 0 (
    echo An error occurred while running the application.
    pause
    exit /b 1
)

REM Deactivate the virtual environment
deactivate

echo Application closed successfully.
pause