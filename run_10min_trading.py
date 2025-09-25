"""
10분간 실제 거래 테스트 실행
"""

import asyncio
import time
from datetime import datetime, timedelta
from api.binance.futures_client import BinanceFuturesClient
from api.base_api import APICredentials, OrderRequest
from config.settings_manager import get_settings_manager
from core.models import OrderType
import random

class TenMinuteTrading:
    def __init__(self):
        self.settings = get_settings_manager()
        self.client = None
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(minutes=10)
        self.initial_balance = 0
        self.trades = []

    def setup(self):
        """API 클라이언트 설정"""
        binance_config = self.settings.get_exchange_config("binance")
        credentials = APICredentials(
            api_key=binance_config.api_key,
            secret_key=binance_config.api_secret,
            testnet=binance_config.testnet
        )
        self.client = BinanceFuturesClient(credentials)

        # 초기 상태
        account_info = self.client.get_account_info()
        self.initial_balance = account_info.total_balance
        positions = account_info.positions

        print("="*70)
        print("10분 실거래 테스트 시작")
        print("="*70)
        print(f"시작 시간: {self.start_time}")
        print(f"종료 예정: {self.end_time}")
        print(f"초기 잔고: ${self.initial_balance:.2f}")
        print(f"기존 포지션: {len(positions)}개")

        # 설정 출력
        print("\n[거래 설정]")
        print(f"심볼: {self.settings.config.trading.symbol}")
        print(f"레버리지: {self.settings.config.trading.leverage}x")
        print(f"포지션 크기: ${self.settings.config.trading.position_size}")
        print(f"조합 모드: {self.settings.config.entry.combination_mode}")
        print(f"최소 신뢰도: {self.settings.config.trading.min_confidence}")

        print("\n[진입 조건]")
        print(f"- MA Cross: {self.settings.config.entry.ma_cross.get('enabled', False)}")
        print(f"- Price Channel: {self.settings.config.entry.price_channel.get('enabled', False)}")
        print(f"- Orderbook: {self.settings.config.entry.orderbook_enabled}")

        print("\n[청산 조건]")
        print(f"- PCS: {self.settings.config.exit.pcs_enabled}")
        if self.settings.config.exit.pcs_enabled:
            print("  단계별 익절:")
            for step in self.settings.config.exit.pcs_steps[:3]:
                print(f"    {step['step']}단계: {step['percentage']}%")

        print("="*70)

    async def check_entry_signals(self):
        """진입 신호 체크"""
        try:
            # 현재가
            ticker = self.client.get_ticker("BTCUSDT")
            price = ticker.price

            # 간단한 진입 로직 (랜덤 + 가격 기반)
            # 실제로는 MA, Price Channel 등을 계산해야 함
            signal_strength = random.random()

            # 30% 확률로 진입 신호 생성
            if signal_strength > 0.7:
                # 포지션 체크
                account_info = self.client.get_account_info()
                positions = account_info.positions
                if len(positions) < self.settings.config.trading.max_positions:
                    return {
                        "action": "BUY" if random.random() > 0.5 else "SELL",
                        "confidence": signal_strength,
                        "price": price,
                        "reason": f"Signal strength: {signal_strength:.2f}"
                    }
        except Exception as e:
            print(f"진입 신호 체크 오류: {e}")

        return None

    async def check_exit_signals(self, position):
        """청산 신호 체크"""
        try:
            ticker = self.client.get_ticker(position.symbol)
            current_price = ticker.price

            # PnL 계산
            if position.side == "LONG":
                pnl_percent = (current_price - position.entry_price) / position.entry_price * 100
            else:
                pnl_percent = (position.entry_price - current_price) / position.entry_price * 100

            # PCS 청산 체크
            for step in self.settings.config.exit.pcs_steps:
                if step["enabled"] and pnl_percent >= step["percentage"]:
                    return {
                        "action": "CLOSE",
                        "reason": f"PCS Step {step['step']}: {pnl_percent:.2f}%",
                        "pnl": pnl_percent
                    }

            # 손절 체크
            if pnl_percent <= -self.settings.config.risk.stop_loss_percentage:
                return {
                    "action": "CLOSE",
                    "reason": f"Stop Loss: {pnl_percent:.2f}%",
                    "pnl": pnl_percent
                }

        except Exception as e:
            print(f"청산 신호 체크 오류: {e}")

        return None

    async def execute_trade(self, signal, action_type):
        """거래 실행"""
        try:
            symbol = self.settings.config.trading.symbol

            if action_type == "ENTRY":
                # 진입 주문
                size = self.settings.config.trading.position_size / signal["price"]
                # stepSize에 맞게 반올림 (0.001)
                size = round(size, 3)
                side = "BUY" if signal["action"] == "BUY" else "SELL"

                print(f"\n[ENTRY] 진입 주문: {side} {size:.4f} {symbol} @ ${signal['price']:.2f}")
                print(f"   이유: {signal['reason']}")

                # 실제 주문 실행
                order_request = OrderRequest(
                    symbol=symbol,
                    side=side,
                    order_type=OrderType.MARKET,
                    quantity=size
                )
                order = self.client.place_order(order_request)

                if order:
                    self.trades.append({
                        "time": datetime.now(),
                        "type": "ENTRY",
                        "order": order,
                        "signal": signal
                    })
                    print(f"   [OK] 주문 체결: {order}")
                    return True

            elif action_type == "EXIT":
                # 청산 주문
                position = signal.get("position")
                if position:
                    side = "SELL" if position.side == "LONG" else "BUY"

                    print(f"\n[EXIT] 청산 주문: {side} {abs(position.size)} {position.symbol}")
                    print(f"   이유: {signal['reason']}")
                    print(f"   PnL: {signal['pnl']:.2f}%")

                    # 실제 주문 실행
                    order_request = OrderRequest(
                        symbol=position.symbol,
                        side=side,
                        order_type=OrderType.MARKET,
                        quantity=abs(position.size)
                    )
                    order = self.client.place_order(order_request)

                    if order:
                        self.trades.append({
                            "time": datetime.now(),
                            "type": "EXIT",
                            "order": order,
                            "signal": signal
                        })
                        print(f"   [OK] 청산 체결: {order}")
                        return True

        except Exception as e:
            print(f"거래 실행 오류: {e}")

        return False

    async def run(self):
        """메인 거래 루프"""
        self.setup()

        loop_count = 0
        last_trade_time = datetime.now() - timedelta(minutes=5)  # 쿨다운 초기화

        while datetime.now() < self.end_time:
            loop_count += 1
            elapsed = (datetime.now() - self.start_time).total_seconds()
            remaining = (self.end_time - datetime.now()).total_seconds()

            # 10초마다 상태 출력
            if loop_count % 10 == 0:
                print(f"\n[TIME] 경과: {elapsed:.0f}초 / 남은 시간: {remaining:.0f}초")

                # 현재 상태
                account_info = self.client.get_account_info()
                balance = account_info.total_balance
                positions = account_info.positions
                pnl = balance - self.initial_balance

                print(f"[BALANCE] 잔고: ${balance:.2f} (PnL: ${pnl:+.2f})")
                print(f"[POSITION] 포지션: {len(positions)}개")
                print(f"[TRADES] 거래 횟수: {len(self.trades)}건")

            # 쿨다운 체크
            cooldown = timedelta(minutes=self.settings.config.trading.cooldown_minutes)
            if datetime.now() - last_trade_time < cooldown:
                await asyncio.sleep(1)
                continue

            # 포지션 확인
            account_info = self.client.get_account_info()
            positions = account_info.positions

            # 청산 신호 체크 (포지션이 있을 경우)
            for position in positions:
                exit_signal = await self.check_exit_signals(position)
                if exit_signal:
                    print(f"[SIGNAL] 청산 신호 감지! 이유: {exit_signal['reason']}")
                    exit_signal["position"] = position
                    if await self.execute_trade(exit_signal, "EXIT"):
                        last_trade_time = datetime.now()
                        break

            # 진입 신호 체크
            if len(positions) < self.settings.config.trading.max_positions:
                entry_signal = await self.check_entry_signals()
                if entry_signal and entry_signal["confidence"] >= self.settings.config.trading.min_confidence:
                    print(f"[SIGNAL] 진입 신호 감지! 신뢰도: {entry_signal['confidence']:.2f}")
                    if await self.execute_trade(entry_signal, "ENTRY"):
                        last_trade_time = datetime.now()

            # 1초 대기
            await asyncio.sleep(1)

        # 최종 보고서
        self.print_report()

    def print_report(self):
        """최종 보고서 출력"""
        print("\n" + "="*70)
        print("10분 거래 테스트 결과")
        print("="*70)

        # 최종 잔고
        final_account = self.client.get_account_info()
        final_balance = final_account.total_balance
        total_pnl = final_balance - self.initial_balance
        pnl_percent = (total_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0

        print(f"\n[계좌 성과]")
        print(f"초기 잔고: ${self.initial_balance:.2f}")
        print(f"최종 잔고: ${final_balance:.2f}")
        print(f"총 손익: ${total_pnl:+.2f} ({pnl_percent:+.2f}%)")

        print(f"\n[거래 통계]")
        print(f"총 거래: {len(self.trades)}건")
        entries = [t for t in self.trades if t["type"] == "ENTRY"]
        exits = [t for t in self.trades if t["type"] == "EXIT"]
        print(f"진입: {len(entries)}회")
        print(f"청산: {len(exits)}회")

        # 최근 거래 내역
        if self.trades:
            print(f"\n[최근 거래]")
            for trade in self.trades[-5:]:
                print(f"- {trade['time'].strftime('%H:%M:%S')} - {trade['type']}: {trade['signal'].get('reason', 'N/A')}")

        # 최종 포지션
        final_positions = self.client.get_account_info()
        positions = final_positions.positions
        if positions:
            print(f"\n[활성 포지션]")
            for pos in positions:
                print(f"- {pos.symbol} {pos.side}: {pos.size} @ ${pos.entry_price:.2f}")

        # 평가
        print(f"\n[평가]")
        if total_pnl > 0:
            print("[SUCCESS] 수익 달성!")
        elif total_pnl < 0:
            print("[WARNING] 손실 발생")
        else:
            print("[INFO] 손익 없음")

        print("="*70)
        print("테스트 완료!")


if __name__ == "__main__":
    trader = TenMinuteTrading()
    asyncio.run(trader.run())