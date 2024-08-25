@echo off
echo Starting Image Search App...

REM Check if venv exists in the current directory
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate" (
    call venv\Scripts\activate
) else (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Set environment variable
set KMP_DUPLICATE_LIB_OK=TRUE

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