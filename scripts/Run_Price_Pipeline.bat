@echo off
cd /d "%~dp0.."
python scripts\run_price_pipeline.py --download
if errorlevel 1 (
 echo Price pipeline failed. Review the message above.
) else (
 start "" "outputs\prices\report.html"
)
pause
