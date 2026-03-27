@echo off
setlocal

echo ============================================
echo      Drawing XML Editor Launcher
echo ============================================
echo.

:: Проверка наличия Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.6+ and add it to your system PATH.
    pause
    exit /b 1
)

:: Проверка наличия скрипта
if not exist "drawing_editor.py" (
    echo [ERROR] drawing_editor.py not found in current directory.
    echo Please place this bat file in the same folder as the script.
    pause
    exit /b 1
)

:: Проверка и установка зависимостей
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

python -c "import lxml" >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing lxml...
    pip install lxml
    if %errorlevel% neq 0 (
        echo Failed to install lxml. Please install manually: pip install lxml
        pause
        exit /b 1
    )
)

echo Dependencies OK.
echo.

:: Запуск
echo Starting editor...
python drawing_editor.py

:: Пауза после завершения (для просмотра вывода)
echo.
echo Editor closed. Press any key to exit...
pause >nul