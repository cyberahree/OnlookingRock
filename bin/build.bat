@echo off
setlocal

:: set cwd to project root
cd /d "%~dp0.."

:: require version argument
if "%~1"=="" (
    echo Usage: build.bat ^<version^>
    echo Example: build.bat 1.0.0
    exit /b 1
)

set VERSION=%~1
set NAME=Rockin-v%VERSION%

echo ========================================
echo Building %NAME%...
echo ========================================

:: clean previous build artifacts
if exist "dist" (
    echo Cleaning dist folder...
    rmdir /s /q dist
)

if exist "build\%NAME%" (
    echo Cleaning build folder...
    rmdir /s /q build\%NAME%
)

:: run pyinstaller
echo Running PyInstaller...
python -m PyInstaller --noconfirm --clean --windowed --name %NAME% --onefile --paths src --add-data "src\assets;assets" --icon icon.png --collect-submodules controller.events.modules src\run.py

if %ERRORLEVEL% neq 0 (
    echo ========================================
    echo Build FAILED!
    echo ========================================
    exit /b %ERRORLEVEL%
)

echo ========================================
echo Build complete!
echo Output: dist\%NAME%.exe
echo ========================================

endlocal