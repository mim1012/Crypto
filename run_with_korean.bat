@echo off
REM Windows 콘솔에서 한글 출력을 위한 실행 스크립트
REM UTF-8 코드 페이지로 설정
chcp 65001 > nul
echo 한글 출력 설정 완료 (UTF-8)
echo.
echo 암호화폐 자동매매 시스템 시작...
echo ===================================
python main.py
pause