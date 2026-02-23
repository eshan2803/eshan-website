@echo off
REM Navigate to the directory where this batch file is located
cd /d "%~dp0"

echo ===========================================
echo CAISO LMP Daily Auto-Update
echo Date: %date% %time%
echo ===========================================

REM --- 1. Fetch and generate prices ---
echo.
echo [PYTHON] Fetching prices and updating GeoJSON...
python fetch_caiso_prices.py
set PYERR=%ERRORLEVEL%

if %PYERR% NEQ 0 (
    echo.
    echo [ERROR] Failed to fetch prices.
    goto :done
)

echo.
echo [SUCCESS] Prices updated.

REM --- 2. Sync with remote and push ---
REM Use fetch + reset to avoid pull/rebase conflicts from other dirty files in the repo.
echo.
echo [GIT] Fetching latest from remote...
git fetch origin simbooni
set FETCHERR=%ERRORLEVEL%

if %FETCHERR% NEQ 0 (
    echo [ERROR] Git fetch failed.
    goto :done
)

REM Reset HEAD to match remote (keeps working tree untouched)
git reset origin/simbooni

echo [GIT] Committing changes...
git add -f substations_with_prices.geojson
git commit -m "Auto-update LMP prices for %date%"
set COMMITERR=%ERRORLEVEL%

if %COMMITERR% NEQ 0 (
    echo [WARNING] Nothing new to commit.
    goto :done
)

echo [GIT] Pushing to GitHub...
git push origin simbooni
set PUSHERR=%ERRORLEVEL%

if %PUSHERR% NEQ 0 (
    echo [ERROR] Push failed.
    goto :done
)

echo.
echo [DONE] Data is live.

:done
echo.
echo Press any key to close this window...
pause >nul
