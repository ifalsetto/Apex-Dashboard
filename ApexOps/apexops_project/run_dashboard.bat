@echo off
setlocal
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo Missing venv. Run: py -m venv .venv
  pause
  exit /b 1
)
call .venv\Scripts\activate
streamlit run apexops\dashboard.py
pause
