@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 run_data_pipeline.py
goto finished
:use_python
python run_data_pipeline.py
:finished
if errorlevel 1 goto failed
echo.
echo Open outputs\data\tega\analysis.html for the SQL-backed financial analysis.
pause
exit /b 0
:failed
echo.
echo The data pipeline did not finish. Read the error above.
echo Python 3.11 or later is required.
pause
exit /b 1
