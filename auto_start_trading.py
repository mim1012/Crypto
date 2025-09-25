#!/usr/bin/env python3
"""자동으로 조건 설정 후 거래 시작"""

import time
import logging
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

logger = logging.getLogger("auto_trading")

print("=" * 60)
print("자동 거래 시작 프로그램")
print("=" * 60)

# 1. Trading Engine 초기화
logger.info("Trading Engine 초기화 중...")
settings_manager = get_settings_manager()
config = settings_manager.config
exchange_config = settings_manager.get_exchange_config("binance")

api_connectors = {}
if exchange_config:
    api_connectors["binance"] = BinanceFuturesClient(exchange_config)

trading_engine = TradingEngine(config=config, api_connectors=api_connectors)
logger.info("Trading Engine 초기화 완료")

# 2. 진입 조건 추가
print("\n[진입 조건 설정]")

# MA 조건 추가
ma_config = {
    "type": "ma_cross",
    "enabled": True,
    "params": {
        "short_period": 20,
        "long_period": 50,
        "condition_type": "종가기준 상향돌파"
    }
}
ma_condition = ConditionFactory.create_condition(ma_config)
trading_engine.add_entry_condition(ma_condition)
logger.info(f"[OK] MA 조건 추가: {ma_condition.get_name()}")
print(f"  - MA Cross (20/50) 조건 추가됨")

# PC 조건 추가
pc_config = {
    "type": "price_channel",
    "enabled": True,
    "params": {
        "period": 20,
        "condition_type": "상단 매수"
    }
}
pc_condition = ConditionFactory.create_condition(pc_config)
trading_engine.add_entry_condition(pc_condition)
logger.info(f"[OK] PC 조건 추가: {pc_condition.get_name()}")
print(f"  - Price Channel (20) 조건 추가됨")

# 3. 청산 조건 추가
print("\n[청산 조건 설정]")

# PCS 시스템 추가
from conditions.exit_condition_factory import ExitConditionFactory

pcs_config = {
    "type": "pcs_system",
    "enabled": True,
    "params": {
        "steps": [
            {"tp": 2.0, "sl": 1.0},   # 1단계
            {"tp": 3.0, "sl": 1.5},   # 2단계
            {"tp": 5.0, "sl": 2.0},   # 3단계
        ],
        "active_step": 1
    }
}
pcs_condition = ExitConditionFactory.create_condition(pcs_config)
trading_engine.add_exit_condition(pcs_condition)
logger.info(f"[OK] PCS 조건 추가: {pcs_condition.get_name()}")
print(f"  - PCS 12단계 시스템 추가됨")

# PC 본절 청산 추가
pc_breakeven_config = {
    "type": "pc_breakeven",
    "enabled": True,
    "params": {
        "long_ticks": 10,
        "short_ticks": 10
    }
}
pc_breakeven = ExitConditionFactory.create_condition(pc_breakeven_config)
trading_engine.add_exit_condition(pc_breakeven)
logger.info(f"[OK] PC 본절 청산 추가: {pc_breakeven.get_name()}")
print(f"  - PC 본절 청산 (10틱) 추가됨")

# 4. 현재 조건 요약
print("\n" + "=" * 60)
print("현재 활성화된 조건:")
print("-" * 60)
print(f"진입 조건: {len(trading_engine.entry_conditions)}개")
for i, cond in enumerate(trading_engine.entry_conditions, 1):
    print(f"  {i}. {cond.get_name()}")

print(f"\n청산 조건: {len(trading_engine.exit_conditions)}개")
for i, cond in enumerate(trading_engine.exit_conditions, 1):
    print(f"  {i}. {cond.get_name()}")

# 5. 거래 시작
print("\n" + "=" * 60)
print("거래 시작 중...")
print("=" * 60)

# 거래 활성화
trading_engine.is_trading_enabled = True
logger.info("거래 활성화됨")

# 동기식 거래 시작
success = trading_engine.start_sync()

if success:
    print("\n[OK] 거래가 성공적으로 시작되었습니다!")
    logger.info("====== 거래 시작됨 ======")
    logger.info(f"진입 조건: {len(trading_engine.entry_conditions)}개")
    logger.info(f"청산 조건: {len(trading_engine.exit_conditions)}개")
    logger.info("========================")

    print("\n실시간 로그 확인:")
    print("  - trading_system.log 파일")
    print("  - realtime_monitor.py 실행 중")
    print("\n거래가 진행 중입니다...")
    print("종료하려면 Ctrl+C를 누르세요.")

    # 계속 실행
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n거래 중지 중...")
        trading_engine.stop()
        print("거래가 중지되었습니다.")
else:
    print("\n[ERROR] 거래 시작 실패")
    logger.error("거래 시작 실패")