#!/usr/bin/env python3
"""거래 시작 시뮬레이션 - 실시간 가격 포함"""

import logging
import time

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 거래 엔진 동기식 시작
engine_logger = logging.getLogger("core.trading_engine")
gui_logger = logging.getLogger("gui.main_window")

gui_logger.info("실시간 모니터링 창이 열렸습니다")
engine_logger.info("거래 엔진 동기식 시작")
engine_logger.info("거래 루프가 백그라운드에서 시작되었습니다")
gui_logger.info("Trading Engine 시작됨")

# 실제 Trading Engine 시뮬레이션
from config.settings_manager import get_settings_manager
from api.binance.futures_client import BinanceFuturesClient

settings_manager = get_settings_manager()
exchange_config = settings_manager.get_exchange_config("binance")

if exchange_config:
    client = BinanceFuturesClient(exchange_config)

    engine_logger.info("====== 거래 루프 시작 ======")
    engine_logger.info("진입 조건 수: 0개")
    engine_logger.info("청산 조건 수: 0개")
    engine_logger.info("거래 활성화: True")
    engine_logger.info("조합 모드: OR")
    engine_logger.info("============================")

    for i in range(5):
        engine_logger.info(f"거래 사이클 #{i+1} 시작")
        engine_logger.info("[1/4] 시장 데이터 수집 시작...")

        # 실시간 가격 가져오기
        market_data = client.get_market_data("BTCUSDT")
        if market_data:
            engine_logger.info(f"  - binance: 가격=${market_data.current_price:,.2f}")
        else:
            engine_logger.info("  - binance: 가격=$50,000.00 (기본값)")

        engine_logger.warning("[2/4] 진입 조건 없음 - 진입 조건을 설정하세요!")
        engine_logger.warning("[3/4] 청산 조건 없음 - 청산 조건을 설정하세요!")
        engine_logger.info("[4/4] 실행할 신호 없음 - 대기")
        engine_logger.info(f"거래 사이클 #{i+1} 완료")
        time.sleep(1)

print("\n거래 시작 시뮬레이션 완료!")
print("trading_system.log에서 실시간 BTC 가격을 확인하세요")