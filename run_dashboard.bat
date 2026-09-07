@echo off
title CadastralAI Dashboard Launcher
cd /d "%~dp0"
echo =========================================================
echo  Starting CadastralAI Streamlit Web-GIS Dashboard...
echo =========================================================
python -m streamlit run app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred. Please check Python and package installation.
    pause
)
