@echo off
chcp 65001 > NUL
title 중복 이미지 검사 프로그램
cd /d "%~dp0"
echo [중복 이미지 검사 프로그램] 실행 중...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [오류] 프로그램 실행 중 문제가 발생했습니다.
    echo 아래 명령어로 필요 라이브러리를 설치해 주세요:
    echo pip install PyQt6 Pillow
    echo.
    pause
)
