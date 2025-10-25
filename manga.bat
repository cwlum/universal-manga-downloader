@echo off
REM Windows launcher that ensures dependencies before starting the app.
python "%~dp0\bootstrap.py" %*
