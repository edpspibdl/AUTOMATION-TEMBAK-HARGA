@echo off
cd /d "%~dp0"
python main.py --auto >> log\run.log 2>&1

