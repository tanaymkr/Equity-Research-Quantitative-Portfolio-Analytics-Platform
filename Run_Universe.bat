@echo off
cd /d "%~dp0"
python run_universe.py --download
if errorlevel 1 (
 echo Universe pipeline failed. If NSE blocked the download, see START_UNIVERSE.md for the manual import.
) else (
 start "" "outputs\universe\NIFTY100\report.html"
)
pause
