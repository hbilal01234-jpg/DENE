@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe py -3.12 -m venv .venv
if errorlevel 1 goto hata
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto hata
start "" http://localhost:8765
.venv\Scripts\python.exe server.py
:hata
pause
