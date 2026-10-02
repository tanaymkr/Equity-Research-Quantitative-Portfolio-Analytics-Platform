@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 run_wabag_forecast.py
goto finished
:use_python
python run_wabag_forecast.py
:finished
if errorlevel 1 goto failed
echo.
echo Open outputs\forecasts\wabag\forecast.html for linked statements, schedules and DCF.
pause
exit /b 0
:failed
echo.
echo The forecast did not finish. Read the error above.
echo Python 3.11 or later is required.
pause
exit /b 1
