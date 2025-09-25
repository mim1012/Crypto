#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 거래 디버깅 모니터
"""

import time
import os
import sys
from datetime import datetime
from colorama import init, Fore, Style

# colorama 초기화
init()

def clear_screen():
    """화면 클리어"""
    os.system('cls' if os.name == 'nt' else 'clear')

def read_last_lines(filename, lines=50):
    """파일의 마지막 N줄 읽기"""
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except:
        return []

def format_log_line(line):
    """로그 라인 포맷팅 및 색상 적용"""
    if 'ERROR' in line or '오류' in line:
        return Fore.RED + line.strip() + Style.RESET_ALL
    elif 'WARNING' in line or '경고' in line:
        return Fore.YELLOW + line.strip() + Style.RESET_ALL
    elif '거래 시작' in line or 'Trading Engine 시작' in line:
        return Fore.GREEN + Style.BRIGHT + line.strip() + Style.RESET_ALL
    elif '진입 신호' in line or 'entry signal' in line.lower():
        return Fore.CYAN + line.strip() + Style.RESET_ALL
    elif '청산 신호' in line or 'exit signal' in line.lower():
        return Fore.MAGENTA + line.strip() + Style.RESET_ALL
    elif '주문' in line or 'order' in line.lower():
        return Fore.BLUE + Style.BRIGHT + line.strip() + Style.RESET_ALL
    elif '포지션' in line or 'position' in line.lower():
        return Fore.GREEN + line.strip() + Style.RESET_ALL
    elif 'DEBUG' in line:
        return Fore.WHITE + Style.DIM + line.strip() + Style.RESET_ALL
    elif '거래 루프' in line or 'trading_loop' in line:
        return Fore.YELLOW + Style.BRIGHT + line.strip() + Style.RESET_ALL
    elif '조건 충족' in line or '조건 평가' in line:
        return Fore.CYAN + Style.BRIGHT + line.strip() + Style.RESET_ALL
    else:
        return line.strip()

def monitor_trading():
    """거래 모니터링"""
    log_file = 'trading_system.log'
    last_size = 0

    print(Fore.GREEN + Style.BRIGHT)
    print("="*70)
    print("            실시간 거래 디버깅 모니터 v2.0")
    print("="*70)
    print(Style.RESET_ALL)
    print(f"로그 파일: {log_file}")
    print("모니터링 시작... (Ctrl+C로 종료)")
    print("-"*70)

    # 초기 로그 표시
    initial_lines = read_last_lines(log_file, 20)
    for line in initial_lines:
        if line.strip():
            print(format_log_line(line))

    print("\n" + "="*70)
    print(Fore.YELLOW + "실시간 업데이트 대기중..." + Style.RESET_ALL)
    print("="*70 + "\n")

    # 주요 상태 변수
    trading_active = False
    last_signal = None
    position_count = 0

    try:
        while True:
            current_size = os.path.getsize(log_file) if os.path.exists(log_file) else 0

            if current_size != last_size:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_size)
                    new_lines = f.readlines()

                for line in new_lines:
                    if line.strip():
                        # 특별한 이벤트 감지
                        formatted_line = format_log_line(line)

                        # 시간 추가
                        timestamp = datetime.now().strftime("[%H:%M:%S]")
                        print(f"{Fore.WHITE}{Style.DIM}{timestamp}{Style.RESET_ALL} {formatted_line}")

                        # 중요 이벤트 강조
                        if '거래 엔진 시작' in line or 'Trading Engine 시작' in line:
                            trading_active = True
                            print(Fore.GREEN + Style.BRIGHT + "  >>> 거래 활성화됨! <<<" + Style.RESET_ALL)

                        elif '거래 엔진 중지' in line or 'Trading Engine 중지' in line:
                            trading_active = False
                            print(Fore.RED + Style.BRIGHT + "  >>> 거래 중지됨! <<<" + Style.RESET_ALL)

                        elif '진입 신호' in line or 'Entry signal' in line:
                            print(Fore.CYAN + Style.BRIGHT + "  >>> 매수 신호 감지! <<<" + Style.RESET_ALL)
                            last_signal = 'ENTRY'

                        elif '청산 신호' in line or 'Exit signal' in line:
                            print(Fore.MAGENTA + Style.BRIGHT + "  >>> 매도 신호 감지! <<<" + Style.RESET_ALL)
                            last_signal = 'EXIT'

                        elif '주문 실행' in line or 'Order executed' in line:
                            print(Fore.BLUE + Style.BRIGHT + "  >>> 주문이 실행되었습니다! <<<" + Style.RESET_ALL)

                        elif '조건 충족' in line:
                            print(Fore.YELLOW + "  >>> 거래 조건이 충족되었습니다 <<<" + Style.RESET_ALL)

                        elif '거래 사이클' in line or 'trading cycle' in line.lower():
                            print(Fore.WHITE + Style.DIM + "  [거래 사이클 실행중...]" + Style.RESET_ALL)

                        elif '시장 데이터' in line or 'market data' in line.lower():
                            print(Fore.WHITE + Style.DIM + "  [시장 데이터 수집중...]" + Style.RESET_ALL)

                last_size = current_size

            # 상태바 업데이트
            status = "활성" if trading_active else "대기"
            status_color = Fore.GREEN if trading_active else Fore.YELLOW

            sys.stdout.write(f"\r{status_color}[상태: {status}] {Style.RESET_ALL}")
            sys.stdout.write(f"마지막 신호: {last_signal if last_signal else 'None'} ")
            sys.stdout.write(f"| 대기중... ")
            sys.stdout.flush()

            time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}모니터링 종료{Style.RESET_ALL}")
        print("="*70)

if __name__ == "__main__":
    monitor_trading()