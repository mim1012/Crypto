#!/usr/bin/env python3
"""조건 추가 후 거래 시작 시뮬레이션"""

import logging
import time
from config.settings_manager import get_settings_manager
from api.binance.futures_client import BinanceFuturesClient
from core.trading_engine import TradingEngine
from conditions.condition_factory import ConditionFactory

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("core.trading_engine")
gui_logger = logging.getLogger("gui.tabs.entry_tab")

print("=" * 50)
print("조건 설정 후 거래 시작 시뮬레이션")
print("=" * 50)

# Trading Engine 생성
settings_manager = get_settings_manager()
config = settings_manager.config
exchange_config = settings_manager.get_exchange_config("binance")

api_connectors = {}
if exchange_config:
    api_connectors["binance"] = BinanceFuturesClient(exchange_config)

# Trading Engine 초기화
logger.info("Trading Engine 초기화")
trading_engine = TradingEngine(config=config, api_connectors=api_connectors)

# 1. MA 조건 추가
print("\n[1] MA 조건 추가...")
gui_logger.info("체크박스 상태 변경: state=2")
gui_logger.info("update_trading_conditions 호출됨")

ma_config = {
    "type": "ma_cross",
    "enabled": True,
    "params": {
        "short_period": 20,
        "long_period": 50,
        "condition_type": "종가기준 상향돌파"
    }
}
condition = ConditionFactory.create_condition(ma_config)
trading_engine.add_entry_condition(condition)
gui_logger.info(f"조건 추가 성공: ma_cross - {condition.get_name()}")

# 2. PC 조건 추가
print("[2] PC 조건 추가...")
pc_config = {
    "type": "price_channel",
    "enabled": True,
    "params": {
        "period": 20,
        "condition_type": "상단 매수"
    }
}
condition = ConditionFactory.create_condition(pc_config)
trading_engine.add_entry_condition(condition)
gui_logger.info(f"조건 추가 성공: price_channel - {condition.get_name()}")

print(f"\n현재 진입 조건 수: {len(trading_engine.entry_conditions)}개")

# 3. 거래 시작
print("\n[3] 거래 시작...")
logger.info("거래 엔진 동기식 시작")
trading_engine.is_running = True
trading_engine.is_trading_enabled = True

# 거래 루프 시뮬레이션
logger.info("====== 거래 루프 시작 ======")
logger.info(f"진입 조건 수: {len(trading_engine.entry_conditions)}개")
logger.info(f"청산 조건 수: {len(trading_engine.exit_conditions)}개")
logger.info(f"거래 활성화: {trading_engine.is_trading_enabled}")
logger.info(f"조합 모드: {trading_engine.combination_mode}")
logger.info("=============================")

# 시장 데이터 수집 및 조건 평가
for cycle in range(3):
    logger.info(f"거래 사이클 #{cycle+1} 시작")
    logger.info("[1/4] 시장 데이터 수집 시작...")

    # 실시간 가격 가져오기
    market_data = api_connectors["binance"].get_market_data("BTCUSDT")
    logger.info(f"  - binance: 가격=${market_data.current_price:,.2f}")

    # 진입 조건 평가
    if len(trading_engine.entry_conditions) > 0:
        logger.info(f"[2/4] 진입 조건 평가 중... (총 {len(trading_engine.entry_conditions)}개 조건)")
        for i, cond in enumerate(trading_engine.entry_conditions, 1):
            logger.info(f"  - 조건 {i}: {cond.get_name()} (활성)")
        logger.info("  결과: 진입 신호 없음")
    else:
        logger.warning("[2/4] 진입 조건 없음 - 진입 조건을 설정하세요!")

    # 청산 조건
    logger.warning("[3/4] 청산 조건 없음 - 청산 조건을 설정하세요!")
    logger.info("[4/4] 실행할 신호 없음 - 대기")
    logger.info(f"거래 사이클 #{cycle+1} 완료")
    time.sleep(1)

print("\n테스트 완료!")
print("로그를 확인하세요: '진입 조건 평가 중...'이 나타나야 합니다.")