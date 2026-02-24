@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo.
echo ========================================
echo VRChat Pavlok Connector
echo ========================================
echo.

REM 仮想環境が存在しない場合は作成
if not exist "venv" (
    echo [Setup] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Python is not installed
        echo Please install Python 3.8 or higher
        pause
        exit /b 1
    )
    echo.
)

REM 仮想環境を有効化
call venv\Scripts\activate.bat

REM 依存ライブラリをチェック・インストール
echo [Setup] Checking dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [Starting] Launching VRChat Pavlok Connector...
echo.

REM メイン実行
python src\main.py

REM 終了時にポーズを表示
echo.
pause
