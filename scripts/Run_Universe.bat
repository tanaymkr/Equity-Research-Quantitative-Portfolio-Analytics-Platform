@echo off
cd /d "%~dp0.."
python scripts\run_universe.py --download
if errorlevel 1 (
 echo Universe pipeline failed. If NSE blocked the download, see docs\guides\universe.md for the manual import.
) else (
 start "" "outputs\universe\NIFTY100\report.html"
)
pause
