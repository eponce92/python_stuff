@echo off
echo Starting Image Search App...

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Run the Python script
python main.py

REM Deactivate the virtual environment
deactivate

echo Application closed.
pause