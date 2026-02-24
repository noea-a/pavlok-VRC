@echo off
chcp 65001 > nul
REM ===== VRChat Pavlok Connector Test Runner =====

setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%venv"
set "TESTS_DIR=%PROJECT_DIR%tests"
set "SRC_DIR=%PROJECT_DIR%src"

REM 仮想環境の確認
if not exist "%VENV_DIR%" (
    echo [エラー] 仮想環境が見つかりません
    pause
    exit /b 1
)

REM 仮想環境を有効化
call "%VENV_DIR%\Scripts\activate.bat"

REM テストディレクトリに移動
cd /d "%PROJECT_DIR%"

echo.
echo ===== Unit Tests: Strong/Weak Detection =====
python tests\test_pavlok.py

echo.
echo ===== Integration Tests: Logic Simulation =====
python tests\test_integration.py

echo.
echo [完了] すべてのテストが実行されました
endlocal
pause
