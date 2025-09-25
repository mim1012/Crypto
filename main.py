#!/usr/bin/env python3
"""
암호화폐 자동매매 시스템 메인 실행 파일

작성자: Manus AI
버전: 2.0
날짜: 2025-01-16
"""

import sys
import asyncio
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from config.settings_manager import get_settings_manager
from core.trading_engine import TradingEngine
from api.binance.futures_client import BinanceFuturesClient
from api.bybit.futures_client import BybitFuturesClient
from gui.main_window import MainWindow
from utils.logger import setup_logger


def main():
    """메인 실행 함수"""
    # 로깅 설정
    logger = setup_logger()
    logger.info("암호화폐 자동매매 시스템 시작")
    
    try:
        # 설정 관리자 초기화
        settings_manager = get_settings_manager()
        config = settings_manager.config
        logger.info("설정 관리자 초기화 완료")
        
        # Qt 애플리케이션 생성
        app = QApplication(sys.argv)
        app.setApplicationName("암호화폐 자동매매 시스템")
        app.setApplicationVersion("2.0")
        
        # API 커넥터 생성
        api_connectors = {}

        # config.json에서 실제 API 설정 읽기
        try:
            from api.base_api import APICredentials

            # 설정에서 거래소 정보 확인
            for exchange in config.exchanges:
                if exchange.enabled and exchange.api_key and exchange.secret_key:
                    credentials = APICredentials(
                        api_key=exchange.api_key,
                        secret_key=exchange.secret_key,
                        testnet=exchange.testnet
                    )

                    if exchange.name == "binance":
                        api_connectors["binance"] = BinanceFuturesClient(credentials)
                        logger.info("바이낸스 API 커넥터 생성 완료")
                    elif exchange.name == "bybit":
                        api_connectors["bybit"] = BybitFuturesClient(credentials)
                        logger.info("바이비트 API 커넥터 생성 완료")

            if not api_connectors:
                logger.warning("활성화된 거래소 API가 없습니다. config.json에서 API 키를 설정해주세요.")

        except Exception as e:
            logger.error(f"API 커넥터 생성 중 오류: {e}")
            api_connectors = {}
        
        # 거래 엔진 생성
        try:
            # config.trading이 이미 TradingConfig 객체임
            # 하지만 전체 config도 필요할 수 있으므로 전달
            trading_engine = TradingEngine(
                config=config,  # 전체 AppConfig 객체 전달
                api_connectors=api_connectors
            )
            logger.info(f"거래 엔진 생성 완료: {trading_engine}")
        except Exception as e:
            logger.error(f"거래 엔진 생성 실패: {e}", exc_info=True)
            # 실패 시 빈 API 커넥터로라도 생성 시도
            try:
                trading_engine = TradingEngine(
                    config=config,
                    api_connectors={}
                )
                logger.warning("빈 API 커넥터로 거래 엔진 생성")
            except Exception as e2:
                logger.error(f"거래 엔진 생성 완전 실패: {e2}", exc_info=True)
                trading_engine = None
        
        # 실시간 데이터 시스템 시작
        from core.data_manager import start_data_manager
        from core.signal_processor import start_signal_processor
        from core.event_system import start_event_system
        
        start_event_system()
        start_data_manager()
        start_signal_processor()
        
        # 메인 윈도우 생성
        main_window = MainWindow(trading_engine)
        main_window.show()
        
        logger.info("GUI 초기화 완료")
        
        # 애플리케이션 실행
        try:
            sys.exit(app.exec_())
        finally:
            # 시스템 종료 처리
            from core.data_manager import stop_data_manager
            from core.signal_processor import stop_signal_processor
            from core.event_system import stop_event_system
            
            stop_signal_processor()
            stop_data_manager()
            stop_event_system()
            logger.info("시스템 종료 완료")
        
    except Exception as e:
        logger.error(f"시스템 시작 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

