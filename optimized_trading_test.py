"""
최적화된 트레이딩 테스트
권장 개선사항 모두 반영
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import time
from api.binance.futures_client import BinanceFuturesClient
from api.base_api import APICredentials
from config.settings_manager import SettingsManager

class OptimizedTradingTest:
    """최적화된 트레이딩 테스트"""

    def __init__(self):
        # 권장 설정 적용
        self.confidence_threshold = 0.5  # 신뢰도 임계값 상향
        self.ma_short = 50  # MA 단기선 (20 -> 50)
        self.ma_long = 200  # MA 장기선 (50 -> 200)
        self.max_positions = 1  # 최대 포지션 1개
        self.cooldown_minutes = 5  # 쿨다운 5분
        self.position_size = 0.001  # 최소 포지션 크기
        self.leverage = 10  # 레버리지 10x

        self.last_trade_time = None
        self.trade_count = 0

        # API 클라이언트 초기화
        self._init_client()

    def _init_client(self):
        """API 클라이언트 초기화"""
        settings_manager = SettingsManager()
        exchange_config = settings_manager.get_exchange_config("binance")

        if not exchange_config or not exchange_config.api_key:
            raise Exception("API 키가 설정되지 않음")

        credentials = APICredentials(
            api_key=exchange_config.api_key,
            secret_key=exchange_config.api_secret,
            testnet=exchange_config.testnet
        )

        self.client = BinanceFuturesClient(credentials)

    def close_existing_positions(self):
        """기존 포지션 청산"""
        try:
            positions = self.client.get_positions()
            for pos in positions:
                if pos.size > 0 and pos.symbol == "BTCUSDT":
                    print(f"기존 포지션 청산 중: {pos.size:.3f} BTC")
                    self.client.close_position("BTCUSDT", 100.0)
                    time.sleep(2)
                    print("청산 완료")
                    return True
        except Exception as e:
            print(f"포지션 청산 오류: {e}")
        return False

    def check_ma_condition(self):
        """MA Cross 조건 확인 (개선된 설정)"""
        try:
            # 캔들 데이터 가져오기
            klines = self.client.get_klines("BTCUSDT", "1m", limit=self.ma_long)

            if len(klines) < self.ma_long:
                return False, 0

            # MA 계산
            closes = [float(k.close_price) for k in klines]
            ma_short = sum(closes[-self.ma_short:]) / self.ma_short
            ma_long = sum(closes[-self.ma_long:]) / self.ma_long

            # 신뢰도 계산
            if ma_long > 0:
                diff_ratio = abs((ma_short - ma_long) / ma_long)
                confidence = min(diff_ratio * 10, 1.0)  # 0~1 범위

                # 개선된 임계값 적용
                if confidence >= self.confidence_threshold:
                    signal = "BUY" if ma_short > ma_long else "SELL"
                    print(f"MA 조건 충족: {signal}, 신뢰도: {confidence:.2f}")
                    return True, confidence

        except Exception as e:
            print(f"MA 조건 확인 오류: {e}")

        return False, 0

    def check_cooldown(self):
        """쿨다운 확인"""
        if self.last_trade_time:
            elapsed = datetime.now() - self.last_trade_time
            if elapsed < timedelta(minutes=self.cooldown_minutes):
                remaining = (timedelta(minutes=self.cooldown_minutes) - elapsed).seconds
                print(f"쿨다운 중... 남은 시간: {remaining}초")
                return False
        return True

    def check_position_limit(self):
        """포지션 제한 확인"""
        try:
            positions = self.client.get_positions()
            active_positions = [p for p in positions if p.size > 0]

            if len(active_positions) >= self.max_positions:
                print(f"최대 포지션 도달: {len(active_positions)}/{self.max_positions}")
                return False

        except Exception as e:
            print(f"포지션 확인 오류: {e}")

        return True

    def execute_trade(self, signal_type):
        """거래 실행"""
        try:
            from api.base_api import OrderRequest, OrderSide, OrderType

            order = OrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY if signal_type == "BUY" else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=self.position_size
            )

            result = self.client.place_order(order)

            if result:
                self.trade_count += 1
                self.last_trade_time = datetime.now()
                print(f"✅ 거래 체결: {result.order_id}")
                print(f"   수량: {self.position_size} BTC")
                print(f"   방향: {signal_type}")
                return True

        except Exception as e:
            print(f"거래 실행 오류: {e}")

        return False

    def run_test(self, duration_minutes=15):
        """최적화된 테스트 실행"""
        print("="*60)
        print("최적화된 트레이딩 테스트 시작")
        print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        print("\n[권장 설정 적용]")
        print(f"신뢰도 임계값: {self.confidence_threshold}")
        print(f"MA 기간: {self.ma_short}/{self.ma_long}")
        print(f"최대 포지션: {self.max_positions}개")
        print(f"쿨다운: {self.cooldown_minutes}분")
        print(f"레버리지: {self.leverage}x")

        # 기존 포지션 청산 옵션
        print("\n기존 포지션 확인...")
        positions = self.client.get_positions()
        active_positions = [p for p in positions if p.size > 0]

        if active_positions:
            print(f"활성 포지션 {len(active_positions)}개 발견")
            # self.close_existing_positions()  # 필요시 주석 해제

        # 초기 잔고
        initial_account = self.client.get_account_info()
        initial_balance = initial_account.total_balance
        print(f"\n초기 잔고: ${initial_balance:,.2f}")

        # 테스트 시작
        start_time = datetime.now()
        check_interval = 30  # 30초마다 확인

        while True:
            try:
                elapsed = (datetime.now() - start_time).seconds

                # 진입 조건 확인
                if elapsed % check_interval == 0:
                    print(f"\n[{elapsed//60}분 경과] 조건 확인 중...")

                    # 1. 쿨다운 확인
                    if not self.check_cooldown():
                        continue

                    # 2. 포지션 제한 확인
                    if not self.check_position_limit():
                        continue

                    # 3. MA 조건 확인
                    ma_signal, confidence = self.check_ma_condition()

                    if ma_signal:
                        print(f"거래 신호 발생! 신뢰도: {confidence:.2f}")
                        self.execute_trade("BUY")

                # 상태 출력 (1분마다)
                if elapsed % 60 == 0 and elapsed > 0:
                    account = self.client.get_account_info()
                    current_pnl = account.unrealized_pnl

                    print(f"\n[상태 업데이트]")
                    print(f"경과 시간: {elapsed//60}분")
                    print(f"거래 횟수: {self.trade_count}")
                    print(f"미실현 PnL: ${current_pnl:,.2f}")

                # 종료 조건
                if elapsed >= duration_minutes * 60:
                    break

                time.sleep(1)

            except KeyboardInterrupt:
                print("\n사용자 중단")
                break
            except Exception as e:
                print(f"테스트 오류: {e}")

        # 최종 결과
        print("\n" + "="*60)
        print("테스트 종료")

        final_account = self.client.get_account_info()
        final_balance = final_account.total_balance
        total_pnl = final_balance - initial_balance

        print(f"초기 잔고: ${initial_balance:,.2f}")
        print(f"최종 잔고: ${final_balance:,.2f}")
        print(f"총 손익: ${total_pnl:,.2f}")
        print(f"수익률: {(total_pnl/initial_balance)*100:+.2f}%")
        print(f"총 거래 횟수: {self.trade_count}")

        if self.trade_count > 0:
            print(f"평균 거래 간격: {duration_minutes/self.trade_count:.1f}분")

        print("="*60)

if __name__ == "__main__":
    test = OptimizedTradingTest()
    test.run_test(duration_minutes=15)  # 15분 테스트