@echo off
cd /d "%~dp0"
start /B "" python "%~dp0lt_client.py" 5000 > "%~dp0lt_client.log" 2>&1
