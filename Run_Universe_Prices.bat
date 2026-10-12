@echo off
cd /d "%~dp0"
if not exist "outputs\universe\NIFTY100\market_config.json" (
 echo Run Run_Universe.bat first to build the Nifty 100 list.
 pause
 exit /b 1
)
python run_price_pipeline.py --download --config outputs\universe\NIFTY100\market_config.json --output outputs\prices\NIFTY100
if errorlevel 1 (
 echo Price download failed. Copy the message above and send it to Claude.
) else (
 start "" "outputs\prices\NIFTY100\report.html"
)
pause
