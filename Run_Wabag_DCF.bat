@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 run_sql_dcf.py
goto finished
:use_python
python run_sql_dcf.py
:finished
if errorlevel 1 goto failed
echo.
echo Open outputs\valuation\wabag\valuation.html for the SQL-backed DCF.
pause
exit /b 0
:failed
echo.
echo The DCF did not finish. Read the error above.
echo Python 3.11 or later is required.
pause
exit /b 1
