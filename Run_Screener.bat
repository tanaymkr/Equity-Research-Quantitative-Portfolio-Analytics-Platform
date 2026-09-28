@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 run_screener.py
goto finished
:use_python
python run_screener.py
:finished
if errorlevel 1 goto failed
echo.
echo Open outputs\screener\screener.html
pause
exit /b 0
:failed
echo.
echo The screener did not finish. Read the error above.
echo If the database is missing, run Run_Wabag_Analysis.bat first.
pause
exit /b 1
