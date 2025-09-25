#!/usr/bin/env python3
"""거래 시작 버튼 누르기"""

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

# GUI MainWindow 찾아서 거래 시작
try:
    from PyQt5.QtWidgets import QApplication
    from gui.main_window import MainWindow

    app = QApplication.instance()
    if app:
        for widget in app.topLevelWidgets():
            if isinstance(widget, MainWindow):
                logger.info("MainWindow 찾음, toggle_trading 호출")
                widget.toggle_trading()
                logger.info("거래 시작 버튼이 눌렸습니다!")
                break
        else:
            logger.error("MainWindow를 찾을 수 없습니다")
    else:
        logger.error("QApplication instance가 없습니다")
except Exception as e:
    logger.error(f"거래 시작 실패: {e}", exc_info=True)