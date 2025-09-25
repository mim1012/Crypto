#!/usr/bin/env python3
"""실시간 조건 평가 모니터링 시스템"""

import sys
import time
import logging
import threading
from datetime import datetime
from colorama import init, Fore, Style, Back
import os

# colorama 초기화
init(autoreset=True)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class RealtimeMonitor:
    """실시간 로그 모니터"""

    def __init__(self):
        self.running = True
        self.last_position = 0

    def clear_screen(self):
        """화면 지우기"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def format_log_line(self, line):
        """로그 라인 포맷팅 및 색상 적용"""
        # 조건 평가 로그 강조
        if "[MA]" in line:
            if "✓ 진입 신호!" in line or "진입 신호!" in line:
                return f"{Back.GREEN}{Fore.WHITE} MA {Style.RESET_ALL} {Fore.GREEN}{line}{Style.RESET_ALL}"
            elif "X 조건 미충족" in line:
                return f"{Back.YELLOW}{Fore.BLACK} MA {Style.RESET_ALL} {Fore.YELLOW}{line}{Style.RESET_ALL}"
            else:
                return f"{Back.BLUE}{Fore.WHITE} MA {Style.RESET_ALL} {line}"

        elif "[PC]" in line:
            if "✓ 진입 신호!" in line or "진입 신호!" in line:
                return f"{Back.GREEN}{Fore.WHITE} PC {Style.RESET_ALL} {Fore.GREEN}{line}{Style.RESET_ALL}"
            elif "X 조건 미충족" in line:
                return f"{Back.YELLOW}{Fore.BLACK} PC {Style.RESET_ALL} {Fore.YELLOW}{line}{Style.RESET_ALL}"
            else:
                return f"{Back.CYAN}{Fore.WHITE} PC {Style.RESET_ALL} {line}"

        # 거래 사이클 로그
        elif "거래 사이클" in line:
            return f"{Fore.MAGENTA}{'='*60}\n{line}\n{'='*60}{Style.RESET_ALL}"

        # 경고 로그
        elif "WARNING" in line or "경고" in line:
            return f"{Fore.RED}⚠️  {line}{Style.RESET_ALL}"

        # 에러 로그
        elif "ERROR" in line or "오류" in line:
            return f"{Back.RED}{Fore.WHITE} ERROR {Style.RESET_ALL} {line}"

        # 정보 로그
        elif "시장 데이터" in line:
            return f"{Fore.CYAN}📊 {line}{Style.RESET_ALL}"

        # 일반 로그
        return line

    def display_header(self):
        """헤더 표시"""
        self.clear_screen()
        print(f"{Back.BLUE}{Fore.WHITE}{'='*80}{Style.RESET_ALL}")
        print(f"{Back.BLUE}{Fore.WHITE}  실시간 거래 조건 모니터링 시스템  {Style.RESET_ALL}")
        print(f"{Back.BLUE}{Fore.WHITE}{'='*80}{Style.RESET_ALL}")
        print(f"\n{Fore.GREEN}[실시간 업데이트 중...]{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}종료: Ctrl+C{Style.RESET_ALL}\n")
        print("-" * 80)

    def monitor_log(self):
        """로그 파일 실시간 모니터링"""
        self.display_header()

        try:
            while self.running:
                with open('trading_system.log', 'r', encoding='utf-8', errors='ignore') as f:
                    # 마지막 위치로 이동
                    f.seek(self.last_position)

                    # 새로운 라인 읽기
                    new_lines = f.readlines()

                    for line in new_lines:
                        line = line.strip()
                        if line:
                            # 조건 평가 관련 로그만 필터링
                            if any(keyword in line for keyword in [
                                "[MA]", "[PC]", "거래 사이클", "진입 조건",
                                "시장 데이터", "현재가", "WARNING", "ERROR",
                                "조건 평가", "신호", "조건 미충족"
                            ]):
                                formatted_line = self.format_log_line(line)
                                print(formatted_line)

                    # 현재 위치 저장
                    self.last_position = f.tell()

                time.sleep(0.1)  # 0.1초마다 체크

        except KeyboardInterrupt:
            print(f"\n{Fore.RED}모니터링 중지됨{Style.RESET_ALL}")
            self.running = False
        except Exception as e:
            print(f"\n{Fore.RED}오류 발생: {e}{Style.RESET_ALL}")

    def display_summary(self):
        """요약 정보 표시"""
        print("\n" + "=" * 80)
        print(f"{Back.CYAN}{Fore.BLACK} 조건 평가 요약 {Style.RESET_ALL}")
        print("-" * 80)

        # 최근 로그 분석
        ma_signals = 0
        pc_signals = 0
        ma_failures = 0
        pc_failures = 0

        try:
            with open('trading_system.log', 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[-100:]  # 최근 100줄 분석

                for line in lines:
                    if "[MA]" in line and "진입 신호!" in line:
                        ma_signals += 1
                    elif "[MA]" in line and "조건 미충족" in line:
                        ma_failures += 1
                    elif "[PC]" in line and "진입 신호!" in line:
                        pc_signals += 1
                    elif "[PC]" in line and "조건 미충족" in line:
                        pc_failures += 1

        except:
            pass

        print(f"MA 조건: {Fore.GREEN}충족 {ma_signals}회{Style.RESET_ALL} / "
              f"{Fore.YELLOW}미충족 {ma_failures}회{Style.RESET_ALL}")
        print(f"PC 조건: {Fore.GREEN}충족 {pc_signals}회{Style.RESET_ALL} / "
              f"{Fore.YELLOW}미충족 {pc_failures}회{Style.RESET_ALL}")
        print("=" * 80)

def main():
    """메인 함수"""
    monitor = RealtimeMonitor()

    # 모니터링 시작
    try:
        monitor.monitor_log()
    finally:
        monitor.display_summary()

if __name__ == "__main__":
    main()