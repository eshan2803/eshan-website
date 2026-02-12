@echo off
REM Navigate to the project directory
cd /d "C:\Users\eshan\OneDrive\Desktop\eshan-website\eshan-website-simbooni_13112025\transmission"

echo ===========================================
echo CAISO LMP Daily Auto-Update
echo Date: %date% %time%
echo ===========================================

REM Run the python script to fetch prices (API v12) and update GeoJSON
python fetch_caiso_prices.py

REM Check if python script succeeded
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to fetch prices.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Prices updated.

REM Sync with remote: fetch latest and reset HEAD to match remote.
REM This avoids pull/rebase conflicts from other dirty files in the repo.
REM Only the price file will be committed; all other working tree changes are untouched.
echo Syncing with remote...
git fetch origin simbooni
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fetch failed.
    pause
    exit /b 1
)

git reset origin/simbooni

echo Committing changes to git...
git add substations_with_prices.geojson
git commit -m "Auto-update LMP prices for %date%"

if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Nothing new to commit.
    exit /b 0
)

echo Pushing to GitHub...
git push origin simbooni

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Push failed.
    pause
    exit /b 1
)

echo.
echo [DONE] Data is live.
