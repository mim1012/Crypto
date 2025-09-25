"""
개선된 트레이딩 테스트
- 신뢰도 임계값 0.5
- 쿨다운 타이머 5분
- 최대 포지션 1개
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from core.trading_engine import TradingEngine
from conditions.ma_cross_condition import MACrossCondition
from conditions.price_channel_condition import PriceChannelCondition
from api.binance.futures_client import BinanceFuturesClient
from api.base_api import APICredentials
from config.settings_manager import SettingsManager
from datetime import datetime, timedelta
import time

class ImprovedTradingSystem:
    def __init__(self):
        self.last_entry_time = None
        self.cooldown_minutes = 5
        self.max_positions = 1
        self.confidence_threshold = 0.5  # 0.01 → 0.5로 상향

    def can_enter_position(self, trading_engine):
        """포지션 진입 가능 여부 확인"""

        # 1. 쿨다운 확인
        if self.last_entry_time:
            elapsed = datetime.now() - self.last_entry_time
            if elapsed < timedelta(minutes=self.cooldown_minutes):
                remaining = (timedelta(minutes=self.cooldown_minutes) - elapsed).seconds
                print(f"⏱️ 쿨다운 중... 남은 시간: {remaining}초")
                return False

        # 2. 최대 포지션 확인
        current_positions = len(trading_engine.positions)
        if current_positions >= self.max_positions:
            print(f"🚫 최대 포지션 도달 ({current_positions}/{self.max_positions})")
            return False

        return True

    def record_entry(self):
        """진입 시간 기록"""
        self.last_entry_time = datetime.now()
        print(f"✅ 진입 시간 기록: {self.last_entry_time.strftime('%H:%M:%S')}")

def main():
    print("="*60)
    print("개선된 트레이딩 시스템 테스트")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 개선된 시스템 생성
    improved_system = ImprovedTradingSystem()

    # PyQt5 애플리케이션 생성
    app = QApplication(sys.argv)

    # GUI 생성
    window = MainWindow()

    # 설정 로드
    settings_manager = SettingsManager()
    exchange_config = settings_manager.get_exchange_config("binance")

    if not exchange_config or not exchange_config.api_key:
        print("❌ API 키가 설정되지 않음")
        return

    # API 클라이언트 생성
    credentials = APICredentials(
        api_key=exchange_config.api_key,
        secret_key=exchange_config.api_secret,
        testnet=exchange_config.testnet
    )

    client = BinanceFuturesClient(credentials)

    # Trading Engine 생성 및 설정
    trading_engine = window.trading_engine
    trading_engine.api_clients["binance"] = client

    # 진입 조건 설정 (개선된 신뢰도)
    ma_condition = MACrossCondition(
        name="MA Cross",
        config={
            "short_period": 20,
            "long_period": 50,
            "confidence_threshold": improved_system.confidence_threshold  # 0.5로 상향
        }
    )

    pc_condition = PriceChannelCondition(
        name="Price Channel",
        config={
            "period": 30,
            "confidence_threshold": improved_system.confidence_threshold  # 0.5로 상향
        }
    )

    # 조건 추가
    trading_engine.clear_entry_conditions()
    trading_engine.add_entry_condition(ma_condition)
    trading_engine.add_entry_condition(pc_condition)

    # 조합 모드 설정 (AND로 변경 - 더 엄격하게)
    trading_engine.set_combination_mode("AND")  # OR → AND

    print("\n【개선된 설정】")
    print(f"✅ 신뢰도 임계값: {improved_system.confidence_threshold}")
    print(f"✅ 쿨다운 타이머: {improved_system.cooldown_minutes}분")
    print(f"✅ 최대 포지션: {improved_system.max_positions}개")
    print(f"✅ 조합 모드: AND (모든 조건 충족 필요)")
    print(f"✅ MA 기간: 20/50")
    print(f"✅ Price Channel 기간: 30")

    # GUI 표시
    window.show()

    # 거래 시작
    print("\n거래 시작...")
    trading_engine.toggle_trading()

    # 모니터링 루프
    async def monitor_trading():
        """개선된 모니터링"""
        start_time = datetime.now()

        while True:
            try:
                elapsed = (datetime.now() - start_time).seconds

                # 5분마다 상태 출력
                if elapsed % 300 == 0:
                    print(f"\n⏰ 경과 시간: {elapsed//60}분")

                    # 포지션 확인
                    positions = client.get_positions()
                    if positions:
                        for pos in positions:
                            if pos.size > 0:
                                print(f"📊 포지션: {pos.symbol} {pos.side} {pos.size:.3f} @ ${pos.entry_price:,.2f}")
                                print(f"   PnL: ${pos.unrealized_pnl:,.2f} ({pos.percentage:+.2f}%)")
                    else:
                        print("📊 포지션 없음")

                    # 계좌 정보
                    account = client.get_account_info()
                    print(f"💰 잔액: ${account.total_balance:,.2f}")
                    print(f"   미실현 PnL: ${account.unrealized_pnl:,.2f}")

                # 진입 가능 여부 확인 (1분마다)
                if elapsed % 60 == 0:
                    if improved_system.can_enter_position(trading_engine):
                        print("✅ 진입 가능 상태")

                await asyncio.sleep(1)

                # 15분 후 종료
                if elapsed >= 900:
                    print("\n⏱️ 15분 테스트 완료")
                    break

            except KeyboardInterrupt:
                print("\n사용자 중단")
                break
            except Exception as e:
                print(f"모니터링 오류: {e}")

    # 비동기 실행
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(monitor_trading())
    finally:
        # 거래 중지
        if trading_engine.is_trading:
            trading_engine.toggle_trading()

        print("\n거래 종료")

        # 최종 수익률 확인
        account = client.get_account_info()
        positions = client.get_positions()

        print("\n" + "="*60)
        print("【최종 결과】")
        print(f"총 잔액: ${account.total_balance:,.2f}")
        print(f"미실현 PnL: ${account.unrealized_pnl:,.2f}")

        if account.total_balance > 0:
            profit_rate = (account.unrealized_pnl / account.total_balance) * 100
            print(f"수익률: {profit_rate:+.2f}%")

        if positions:
            active_positions = [p for p in positions if p.size > 0]
            print(f"활성 포지션: {len(active_positions)}개")

        print("="*60)

if __name__ == "__main__":
    main()