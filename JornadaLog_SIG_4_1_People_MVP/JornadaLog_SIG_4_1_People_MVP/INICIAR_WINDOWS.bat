@echo off
cd /d "%~dp0"
if not exist .venv python -m venv .venv
call .venv\Scriptsctivate.bat
pip install -r requirements.txt
if not exist .env copy .env.example .env
set DATABASE_TYPE=sqlite
python app.py
pause
