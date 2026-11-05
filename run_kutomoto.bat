@echo off
rem ==============================================================================
rem kutomoto -- Professional Forms Filling Automation System for Windows OS
rem Copyright Notice: Copyrights reserved to 90Studio
rem ==============================================================================
chcp 65001 >nul
title kutomoto Automation System -- 90Studio

echo.
echo  ==============================================================================
echo   kutomoto -- Professional Forms Filling Automation System for Windows OS
echo   Copyrights reserved to 90Studio
echo  ==============================================================================
echo.

cd /d "%~dp0"
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found in your system PATH.
        echo Please install Python 3.10+ from https://python.org or the Microsoft Store.
        echo.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py -3"
    )
) else (
    set "PY_CMD=python"
)

echo [INFO] Launching kutomoto application shell...
%PY_CMD% -m kutomoto --port 8765 %*

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] kutomoto terminated unexpectedly with exit code %errorlevel%.
    pause
)
