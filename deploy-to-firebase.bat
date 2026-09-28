@echo off
cd /d "%~dp0"
title CleanIQ - Deploy to Firebase Hosting
color 0b
echo ===============================================================
echo                CleanIQ Firebase Deployment
echo ===============================================================
echo.
echo [1/3] Building frontend production bundle...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Frontend build failed! Please check errors above.
    cd ..
    pause
    exit /b %errorlevel%
)
cd ..
echo.
echo [2/3] Connecting to Firebase...
echo If not signed in, a browser window will open shortly.
echo.
call firebase login
echo.
echo [3/3] Deploying site to Firebase Hosting (cleaniq-a1f4f)...
call firebase deploy --only hosting
echo.
echo ===============================================================
echo  Your site is live at: https://cleaniq-a1f4f.web.app
echo ===============================================================
pause
