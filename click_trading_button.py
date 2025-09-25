#!/usr/bin/env python3
"""GUI에서 거래 시작 버튼 클릭 시뮬레이션"""

import sys
import time
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow

print("거래 시작 버튼 클릭 시뮬레이션")
print("=" * 50)

# 기존 앱 인스턴스 찾기
app = QApplication.instance()
if app:
    print("✅ 실행중인 GUI를 찾았습니다")

    # MainWindow 찾기
    for widget in app.topLevelWidgets():
        if isinstance(widget, MainWindow):
            print("✅ MainWindow를 찾았습니다")

            # Trading Engine 확인
            if widget.trading_engine:
                print(f"✅ Trading Engine 존재: {widget.trading_engine}")
                print(f"   - is_running: {widget.trading_engine.is_running}")
                print(f"   - is_trading_enabled: {widget.trading_engine.is_trading_enabled}")
            else:
                print("❌ Trading Engine이 없습니다")

            # 거래 버튼 상태 확인
            if hasattr(widget, 'trading_btn'):
                current_text = widget.trading_btn.text()
                print(f"현재 버튼 텍스트: {current_text}")

                if "시작" in current_text:
                    print("\n[ACTION] 거래 시작 버튼 클릭...")
                    widget.toggle_trading()
                    print("✅ 거래 시작됨!")
                else:
                    print("\n[INFO] 거래가 이미 실행중입니다")

                # 10초 대기하며 상태 확인
                print("\n10초간 대기하며 로그 확인...")
                for i in range(10):
                    time.sleep(1)
                    print(f"[{i+1}/10] 대기중...")

                print("\n거래 시작 완료!")
                print("trading_system.log 파일을 확인하세요")
            else:
                print("❌ 거래 버튼을 찾을 수 없습니다")
            break
    else:
        print("❌ MainWindow를 찾을 수 없습니다")
else:
    print("❌ 실행중인 GUI가 없습니다")
    print("먼저 python main.py를 실행해주세요")