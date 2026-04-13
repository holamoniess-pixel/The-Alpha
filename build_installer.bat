@echo off
title Alpha Omega - Windows Installer Builder
color 0A
setlocal enabledelayedexpansion

echo ============================================================
echo        ALPHA OMEGA - WINDOWS INSTALLER BUILDER
echo              Creating Deployment Package
echo ============================================================
echo.

set VERSION=2.1.0
set DIST_DIR=dist\AlphaOmega_v%VERSION%
set PACKAGE_NAME=AlphaOmega_v%VERSION%_Windows

echo [1/6] Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
mkdir "%DIST_DIR%"
mkdir "%DIST_DIR%\src"
mkdir "%DIST_DIR%\logs"
mkdir "%DIST_DIR%\data"
mkdir "%DIST_DIR%\models"
echo.

echo [2/6] Copying source files...
xcopy /s /e /q "src\*" "%DIST_DIR%\src\"
xcopy /q "config.yaml" "%DIST_DIR%\"
xcopy /q "requirements.txt" "%DIST_DIR%\"
xcopy /q "run_alpha.py" "%DIST_DIR%\"
xcopy /q "test_system.py" "%DIST_DIR%\"
echo.

echo [3/6] Copying web interface...
if exist "apps\ui\build" (
    mkdir "%DIST_DIR%\web"
    xcopy /s /e /q "apps\ui\build\*" "%DIST_DIR%\web\"
    echo Web UI copied
) else (
    echo Web UI not built - run 'npm run build' in apps/ui first
)
echo.

echo [4/6] Creating launcher scripts...

echo @echo off > "%DIST_DIR%\Start_AlphaOmega.bat"
echo title Alpha Omega v%VERSION% >> "%DIST_DIR%\Start_AlphaOmega.bat"
echo color 0A >> "%DIST_DIR%\Start_AlphaOmega.bat"
echo echo ============================================================ >> "%DIST_DIR%\Start_AlphaOmega.bat"
echo echo           ALPHA OMEGA v%VERSION% >> "%DIST_DIR%\Start_AlphaOmega.bat"
echo echo      Voice-Activated PC Control System >> "%DIST_DIR%\Start_AlphaOmega.bat"
echo echo ============================================================ >> "%DIST_DIR%\Start_AlphaOmega.bat"
echo echo. >> "%DIST_DIR%\Start_AlphaOmega.bat"
echo echo Starting system... >> "%DIST_DIR%\Start_AlphaOmega.bat"
echo python run_alpha.py >> "%DIST_DIR%\Start_AlphaOmega.bat"
echo pause >> "%DIST_DIR%\Start_AlphaOmega.bat"

echo @echo off > "%DIST_DIR%\Install_Dependencies.bat"
echo echo Installing Alpha Omega dependencies... >> "%DIST_DIR%\Install_Dependencies.bat"
echo python -m pip install --upgrade pip >> "%DIST_DIR%\Install_Dependencies.bat"
echo pip install -r requirements.txt >> "%DIST_DIR%\Install_Dependencies.bat"
echo echo. >> "%DIST_DIR%\Install_Dependencies.bat"
echo echo Dependencies installed! >> "%DIST_DIR%\Install_Dependencies.bat"
echo pause >> "%DIST_DIR%\Install_Dependencies.bat"

echo @echo off > "%DIST_DIR%\Run_Tests.bat"
echo echo Running Alpha Omega tests... >> "%DIST_DIR%\Run_Tests.bat"
echo python test_system.py >> "%DIST_DIR%\Run_Tests.bat"
echo pause >> "%DIST_DIR%\Run_Tests.bat"

echo.

echo [5/6] Creating README...
echo # Alpha Omega v%VERSION% > "%DIST_DIR%\README.txt"
echo. >> "%DIST_DIR%\README.txt"
echo ## Installation >> "%DIST_DIR%\README.txt"
echo. >> "%DIST_DIR%\README.txt"
echo 1. Run Install_Dependencies.bat >> "%DIST_DIR%\README.txt"
echo 2. Run Start_AlphaOmega.bat >> "%DIST_DIR%\README.txt"
echo. >> "%DIST_DIR%\README.txt"
echo ## Features >> "%DIST_DIR%\README.txt"
echo - Voice Control with "Hey Alpha" wake word >> "%DIST_DIR%\README.txt"
echo - 200+ Automation Features >> "%DIST_DIR%\README.txt"
echo - Self-Extension: Creates its own tools >> "%DIST_DIR%\README.txt"
echo - 4-Step Task Execution: Plan→Implement→CrossCheck→Proceed >> "%DIST_DIR%\README.txt"
echo - AES-256 Encrypted Vault >> "%DIST_DIR%\README.txt"
echo - Pattern Learning >> "%DIST_DIR%\README.txt"
echo. >> "%DIST_DIR%\README.txt"
echo ## API >> "%DIST_DIR%\README.txt"
echo - http://localhost:8000 - Dashboard >> "%DIST_DIR%\README.txt"
echo - ws://localhost:8000/ws - WebSocket >> "%DIST_DIR%\README.txt"
echo. >> "%DIST_DIR%\README.txt"
echo Enjoy! >> "%DIST_DIR%\README.txt"
echo.

echo [6/6] Creating ZIP package...
cd dist
powershell -command "Compress-Archive -Path 'AlphaOmega_v%VERSION%' -DestinationPath '%PACKAGE_NAME%.zip' -Force"
cd ..
echo.

echo ============================================================
echo              BUILD COMPLETE!
echo ============================================================
echo.
echo   Package: dist\%PACKAGE_NAME%.zip
echo   Version: %VERSION%
echo.
echo   Contents:
echo   - Source files
echo   - Configuration
echo   - Launcher scripts
echo   - README
echo.
echo ============================================================
pause
