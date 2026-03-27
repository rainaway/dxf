@echo off
setlocal

echo ============================================
echo      Drawing Editor Launcher
echo ============================================
echo.

:: Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ and add it to your system PATH.
    pause
    exit /b 1
)

:: Check if the main script exists
if not exist "drawing_editor\main.py" (
    echo [ERROR] drawing_editor\main.py not found.
    echo Please place this bat file in the project root directory.
    pause
    exit /b 1
)

:: Check and install dependencies
echo Checking dependencies...

python -c "import PyQt5" >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing PyQt5...
    pip install PyQt5
    if %errorlevel% neq 0 (
        echo Failed to install PyQt5. Please install manually: pip install PyQt5
        pause
        exit /b 1
    )
)

python -c "import ezdxf" >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing ezdxf...
    pip install ezdxf
    if %errorlevel% neq 0 (
        echo Failed to install ezdxf. Please install manually: pip install ezdxf
        pause
        exit /b 1
    )
)

echo Dependencies OK.
echo.

:: Run the application
echo Starting editor...
python drawing_editor/main.py

:: Pause after completion
echo.
echo Editor closed. Press any key to exit...
pause >nul
