#!/usr/bin/env python3
"""거래 시작 버튼 누르기 시뮬레이션"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import logging

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def press_trading_button():
    """거래 시작 버튼 누르기"""
    try:
        # 실행중인 앱의 모든 윈도우 찾기
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'trading_btn'):
                logger.info("거래 버튼 찾음!")
                widget.toggle_trading()
                logger.info("거래 시작 버튼 클릭됨!")
                return True
        logger.warning("거래 버튼을 찾을 수 없음")
        return False
    except Exception as e:
        logger.error(f"버튼 클릭 실패: {e}")
        return False

if __name__ == "__main__":
    app = QApplication.instance()
    if not app:
        print("GUI가 실행중이지 않습니다")
        sys.exit(1)

    print("거래 시작 버튼 누르기...")
    if press_trading_button():
        print("✅ 거래 시작 버튼이 눌렸습니다!")
        print("trading_system.log를 확인하세요")
    else:
        print("❌ 버튼 누르기 실패")