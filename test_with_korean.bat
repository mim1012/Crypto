@echo off
REM Windows 콘솔에서 한글 출력을 위한 테스트 실행 스크립트
chcp 65001 > nul
echo 테스트 환경 설정 완료 (UTF-8)
echo.
echo ===================================
echo 테스트를 실행할 번호를 선택하세요:
echo ===================================
echo 1. 통합 테스트 (test_integration.py)
echo 2. 실시간 데이터 테스트 (test_realtime.py)
echo 3. GUI 테스트 (test_gui_headless.py)
echo 4. API 연결 테스트 (test_futures_connection.py)
echo 5. 모든 테스트 실행
echo ===================================
set /p choice="선택 (1-5): "

if "%choice%"=="1" (
    echo.
    echo 통합 테스트 실행 중...
    python test_integration.py
) else if "%choice%"=="2" (
    echo.
    echo 실시간 데이터 테스트 실행 중...
    python test_realtime.py
) else if "%choice%"=="3" (
    echo.
    echo GUI 테스트 실행 중...
    python test_gui_headless.py
) else if "%choice%"=="4" (
    echo.
    echo API 연결 테스트 실행 중...
    python test_futures_connection.py
) else if "%choice%"=="5" (
    echo.
    echo 모든 테스트 순차 실행...
    echo.
    echo [1/4] 통합 테스트...
    python test_integration.py
    echo.
    echo [2/4] 실시간 데이터 테스트...
    timeout /t 3 /nobreak > nul
    python test_realtime.py
    echo.
    echo [3/4] GUI 테스트...
    python test_gui_headless.py
    echo.
    echo [4/4] API 연결 테스트...
    python test_futures_connection.py
) else (
    echo 잘못된 선택입니다.
)

echo.
echo 테스트 완료!
pause