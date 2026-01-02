@echo off
REM Navigate to the directory where this batch file is located
cd /d "%~dp0"

echo ===========================================
echo CAISO LMP Daily Auto-Update
echo Date: %date% %time%
echo ===========================================

REM Run the python script to fetch prices (API v12) and update GeoJSON
python fetch_caiso_prices.py

REM Check if python script succeeded
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Prices updated.
    
    echo Committing changes to git...
    git add substations_with_prices.geojson
    git commit -m "Auto-update LMP prices for %date%"
    
    echo Pushing to GitHub...
    git push
    
    echo.
    echo [DONE] Data is live.
) else (
    echo.
    echo [ERROR] Failed to fetch prices.
    pause
)
