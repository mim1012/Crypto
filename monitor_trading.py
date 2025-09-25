#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 거래 모니터링 도구

이 스크립트는 거래 시스템의 실시간 상태를 모니터링합니다.
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import time
import json
import os
from datetime import datetime
from colorama import init, Fore, Style

# colorama 초기화
init()

def clear_screen():
    """화면 클리어"""
    os.system('cls' if os.name == 'nt' else 'clear')

def read_log_tail(filename, lines=20):
    """로그 파일의 마지막 N줄 읽기"""
    if not os.path.exists(filename):
        return []

    with open(filename, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
        return all_lines[-lines:]

def monitor_trading_system():
    """거래 시스템 실시간 모니터링"""

    print(f"""
{Fore.CYAN}================================================================================
🔍 실시간 거래 모니터링 시스템
================================================================================{Style.RESET_ALL}

{Fore.YELLOW}📊 모니터링 방법:{Style.RESET_ALL}

1. {Fore.GREEN}GUI에서 확인{Style.RESET_ALL}
   ├─ 진입 설정 탭: 실시간 가격, 신호 상태
   ├─ 청산 설정 탭: PCS 단계별 상태
   └─ 포지션 탭: 활성 포지션, 손익

2. {Fore.GREEN}로그 파일 모니터링{Style.RESET_ALL}
   ├─ trading_system.log: 시스템 이벤트
   ├─ logs/trading_YYYYMMDD.log: 거래 상세
   └─ logs/performance_YYYYMMDD.log: 성능 지표

3. {Fore.GREEN}실시간 데이터 확인{Style.RESET_ALL}
   └─ 2초마다 자동 업데이트

{Fore.CYAN}================================================================================{Style.RESET_ALL}
""")

    while True:
        try:
            clear_screen()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"{Fore.CYAN}╔══════════════════════════════════════════════════════════════════════╗")
            print(f"║  📊 실시간 거래 모니터링  |  {current_time}                    ║")
            print(f"╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")

            # 1. Config 정보
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)

                trading_config = config.get("trading", {})
                print(f"{Fore.GREEN}📈 거래 설정:{Style.RESET_ALL}")
                print(f"   심볼: {trading_config.get('symbol', 'N/A')}")
                print(f"   레버리지: {trading_config.get('leverage', 'N/A')}x")
                print(f"   포지션 크기: ${trading_config.get('position_size', 'N/A')}")
                print()

            # 2. 최근 로그 이벤트
            print(f"{Fore.GREEN}📝 최근 시스템 이벤트:{Style.RESET_ALL}")
            log_lines = read_log_tail("trading_system.log", 10)

            for line in log_lines[-5:]:  # 마지막 5줄만 표시
                # 로그 레벨에 따라 색상 적용
                if "ERROR" in line:
                    print(f"   {Fore.RED}• {line.strip()}{Style.RESET_ALL}")
                elif "WARNING" in line or "WARN" in line:
                    print(f"   {Fore.YELLOW}• {line.strip()}{Style.RESET_ALL}")
                elif "거래" in line or "주문" in line or "포지션" in line:
                    print(f"   {Fore.CYAN}• {line.strip()}{Style.RESET_ALL}")
                else:
                    print(f"   • {line.strip()}")

            print()

            # 3. 거래 신호 모니터링
            print(f"{Fore.GREEN}🎯 거래 신호 상태:{Style.RESET_ALL}")

            # 로그에서 신호 관련 메시지 찾기
            signal_found = False
            for line in log_lines:
                if "신호" in line or "Signal" in line or "entry" in line.lower():
                    print(f"   {Fore.YELLOW}• {line.strip()}{Style.RESET_ALL}")
                    signal_found = True

            if not signal_found:
                print(f"   {Fore.GRAY}• 대기 중...{Style.RESET_ALL}")

            print()

            # 4. 포지션 정보 (로그에서 추출)
            print(f"{Fore.GREEN}💼 포지션 상태:{Style.RESET_ALL}")
            position_found = False
            for line in log_lines:
                if "position" in line.lower() or "포지션" in line:
                    print(f"   • {line.strip()}")
                    position_found = True

            if not position_found:
                print(f"   {Fore.GRAY}• 활성 포지션 없음{Style.RESET_ALL}")

            print()

            # 5. API 연결 상태
            print(f"{Fore.GREEN}🔌 API 연결 상태:{Style.RESET_ALL}")
            api_connected = False
            for line in log_lines:
                if "API" in line or "연결" in line:
                    if "성공" in line or "connected" in line.lower():
                        print(f"   {Fore.GREEN}✅ Binance Futures: 연결됨{Style.RESET_ALL}")
                        api_connected = True
                        break

            if not api_connected:
                print(f"   {Fore.YELLOW}⚠️ 연결 상태 확인 중...{Style.RESET_ALL}")

            print(f"\n{Fore.CYAN}{'─'*72}{Style.RESET_ALL}")
            print(f"{Fore.GRAY}[Q 키를 누르면 종료, 5초마다 자동 새로고침]{Style.RESET_ALL}")

            # 5초 대기
            time.sleep(5)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}모니터링 종료{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"\n{Fore.RED}오류: {e}{Style.RESET_ALL}")
            time.sleep(5)

def show_monitoring_guide():
    """모니터링 가이드 표시"""
    print(f"""
{Fore.CYAN}================================================================================
📊 실시간 거래 모니터링 가이드
================================================================================{Style.RESET_ALL}

{Fore.YELLOW}1. GUI에서 실시간 모니터링:{Style.RESET_ALL}

   {Fore.GREEN}[진입 설정 탭]{Style.RESET_ALL}
   • 현재가: 실시간 BTC 가격 (2초 업데이트)
   • PC 범위: Price Channel 상/하한
   • 이평선: MA 값
   • 신호 발생: 진입 신호 카운트

   {Fore.GREEN}[청산 설정 탭]{Style.RESET_ALL}
   • PCS 모니터링 테이블
     - 단계: 1~12단계
     - 상태: 모니터링/활성/대기중/완료
     - 익절률/손절률: 각 단계별 설정값

   {Fore.GREEN}[포지션 탭]{Style.RESET_ALL}
   • 실시간 포지션 목록
   • 총 잔고 / 사용 가능 잔고
   • 미실현 손익
   • 사용 마진

{Fore.YELLOW}2. 로그 파일 실시간 확인:{Style.RESET_ALL}

   {Fore.GREEN}Windows PowerShell:{Style.RESET_ALL}
   Get-Content trading_system.log -Wait -Tail 20

   {Fore.GREEN}CMD (실시간 업데이트):{Style.RESET_ALL}
   type trading_system.log | more

   {Fore.GREEN}로그 필터링:{Style.RESET_ALL}
   findstr "거래" trading_system.log
   findstr "ERROR" trading_system.log
   findstr "신호" trading_system.log

{Fore.YELLOW}3. 거래 신호 확인 포인트:{Style.RESET_ALL}

   ✅ 진입 신호 발생
      - "Entry signal generated"
      - "진입 신호 발생"
      - MA 크로스, PC 돌파 등

   ✅ 주문 실행
      - "Order placed"
      - "주문 실행"
      - Order ID 생성

   ✅ 포지션 생성
      - "Position opened"
      - "포지션 생성"
      - 수량, 가격 표시

   ✅ 청산 실행
      - "Position closed"
      - "포지션 청산"
      - PnL 표시

{Fore.YELLOW}4. 성능 모니터링:{Style.RESET_ALL}

   {Fore.GREEN}API 응답 시간:{Style.RESET_ALL}
   • logs/performance_YYYYMMDD.log 확인
   • 정상: <100ms
   • 경고: 100-500ms
   • 문제: >500ms

   {Fore.GREEN}시스템 리소스:{Style.RESET_ALL}
   • CPU 사용률 확인
   • 메모리 사용량 확인
   • 네트워크 지연 확인

{Fore.YELLOW}5. 문제 해결:{Style.RESET_ALL}

   ❌ 가격 업데이트 안됨
      → API 연결 확인
      → 인터넷 연결 확인

   ❌ 신호 발생 안함
      → 진입 조건 설정 확인
      → 조건 활성화 여부 확인

   ❌ 주문 실행 안됨
      → 계좌 잔고 확인
      → 레버리지 설정 확인
      → API 권한 확인

{Fore.CYAN}================================================================================{Style.RESET_ALL}
""")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--guide":
        show_monitoring_guide()
    else:
        try:
            # colorama 설치 확인
            import colorama
            monitor_trading_system()
        except ImportError:
            print("colorama 모듈 설치 필요: pip install colorama")
            print("\n기본 모니터링 가이드를 표시합니다...")
            show_monitoring_guide()