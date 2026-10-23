@echo off
cd /d "%~dp0.."
rem Rebuild the price config from the stored list first (no download), so a
rem stale config from an earlier run or older code is never reused.
python scripts\run_universe.py
if errorlevel 1 (
 echo Could not build the price config. Run Run_Universe.bat first.
 pause
 exit /b 1
)
python scripts\run_price_pipeline.py --download --config outputs\universe\NIFTY100\market_config.json --output outputs\prices\NIFTY100
if errorlevel 1 (
 echo Price download failed. Review the message above.
) else (
 start "" "outputs\prices\NIFTY100\report.html"
)
pause
