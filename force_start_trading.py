#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
강제로 거래 엔진 시작하기
"""

import asyncio
import logging
from datetime import datetime
from core.trading_engine import TradingEngine
from api.binance.futures_client import BinanceFuturesClient
from config.settings_manager import get_settings_manager

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

async def force_start_trading():
    """거래 엔진 강제 시작"""

    logger.info("=" * 50)
    logger.info("거래 엔진 강제 시작")
    logger.info("=" * 50)

    # API 클라이언트 생성
    settings_manager = get_settings_manager()
    exchange_config = settings_manager.get_exchange_config("binance")

    if not exchange_config:
        logger.error("API 설정이 없습니다!")
        return

    api_client = BinanceFuturesClient(exchange_config)
    logger.info(f"API 클라이언트 생성: {api_client}")

    # Trading Engine 생성
    config = settings_manager.config
    api_connectors = {"binance": api_client}
    trading_engine = TradingEngine(config=config, api_connectors=api_connectors)
    logger.info("Trading Engine 생성 완료")

    # 거래 시작
    logger.info("거래 시작 버튼 클릭 시뮬레이션")
    trading_engine.is_trading_enabled = True

    # 거래 루프 시작
    logger.info("거래 루프 시작...")
    await trading_engine.start()

    # 30초 동안 실행
    for i in range(30):
        await asyncio.sleep(1)
        if i % 5 == 0:
            logger.info(f"거래 실행 중... {i}/30초")

    # 거래 중지
    logger.info("거래 중지...")
    await trading_engine.stop()

    logger.info("=" * 50)
    logger.info("거래 엔진 테스트 완료")
    logger.info("=" * 50)

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("거래 엔진 강제 시작 프로그램")
    print("=" * 50)
    print(f"시작 시간: {datetime.now()}")
    print("30초 동안 거래 엔진을 실행합니다...")
    print("trading_system.log 파일을 확인하세요")
    print("=" * 50 + "\n")

    asyncio.run(force_start_trading())

    print("\n테스트 완료!")