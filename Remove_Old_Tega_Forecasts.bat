@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 scripts\remove_old_tega_forecasts.py
goto finished
:use_python
python scripts\remove_old_tega_forecasts.py
:finished
if errorlevel 1 goto failed
echo.
echo Review the changes in GitHub Desktop, commit, and click Push origin.
pause
exit /b 0
:failed
echo.
echo Cleanup did not finish. Read the error above.
echo Python 3.11 or later must be installed.
pause
exit /b 1
