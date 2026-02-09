@echo off
REM Navigate to the directory where this batch file is located
cd /d "%~dp0"

echo ===========================================
echo CAISO LMP Daily Auto-Update
echo Date: %date% %time%
echo ===========================================

REM --- 1. Git State Cleanup (Auto-Fix) ---
REM Check for and clear any stuck git states from previous failed runs
if exist ".git\rebase-merge" (
    echo [AUTO-FIX] Found stuck rebase. Aborting...
    git rebase --abort
)
if exist ".git\rebase-apply" (
    echo [AUTO-FIX] Found stuck rebase. Aborting...
    git rebase --abort
)
if exist ".git\MERGE_HEAD" (
    echo [AUTO-FIX] Found stuck merge. Aborting...
    git merge --abort
)

REM --- 2. Pull Latest Changes ---
REM We use --rebase --autostash to correctly handle local uncommitted changes
echo.
echo [GIT] Pulling latest changes from GitHub...
git pull --rebase --autostash

REM If pull failed (e.g. conflict), we try to recover
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Git pull failed. Clearing state and continuing...
    REM If the pull left us in a rebase state, abort it so we can at least commit our new data
    if exist ".git\rebase-merge" git rebase --abort
    if exist ".git\rebase-apply" git rebase --abort
)

REM --- 3. Run Generation Script ---
echo.
echo [PYTHON] Fetching prices and updating GeoJSON...
python fetch_caiso_prices.py

REM Check if python script succeeded
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Prices updated.
    
    echo [GIT] Committing changes...
    git add substations_with_prices.geojson
    git commit -m "Auto-update LMP prices for %date%"

    echo [GIT] Pushing to GitHub...
    git push

    REM If push fails (remote has new changes), try one simple retry strategy
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [WARNING] Push failed. Remote is ahead. Retrying sync...
        git pull --rebase --autostash
        git push
    )
    
    echo.
    echo [DONE] Data is live.
) else (
    echo.
    echo [ERROR] Failed to fetch prices.
    pause
)
