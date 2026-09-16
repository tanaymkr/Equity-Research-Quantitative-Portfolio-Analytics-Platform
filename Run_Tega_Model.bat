@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 run_tega_model.py
goto finished
:use_python
python run_tega_model.py
:finished
if errorlevel 1 goto failed
echo.
echo Open outputs\tega_molycop\report.html for all three acquisition scenarios.
pause
exit /b 0
:failed
echo.
echo The model did not finish. Read the error above.
echo Python 3.11 or later must be installed to run this model.
pause
exit /b 1
