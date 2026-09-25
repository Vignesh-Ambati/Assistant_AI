@echo off
title AI Assistant

echo Checking python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import PyQt6" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyQt6...
    pip install PyQt6
    if %errorlevel% neq 0 (
        echo Failed to install PyQt6.
        pause
        exit /b 1
    )
)

echo Running setup...
python setup_model.py
if %errorlevel% neq 0 (
    echo Setup failed.
    pause
    exit /b 1
)

echo Starting AI Assistant...
start pythonw main.py
