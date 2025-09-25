"""
실시간 거래 모니터링
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.binance.futures_client import BinanceFuturesClient
from api.base_api import APICredentials
from config.settings_manager import SettingsManager
from datetime import datetime
import time

def monitor_new_trades():
    """실시간 거래 모니터링"""

    # API 클라이언트 초기화
    settings_manager = SettingsManager()
    exchange_config = settings_manager.get_exchange_config("binance")

    credentials = APICredentials(
        api_key=exchange_config.api_key,
        secret_key=exchange_config.api_secret,
        testnet=exchange_config.testnet
    )

    client = BinanceFuturesClient(credentials)

    print("="*60)
    print("실시간 거래 모니터링 시작")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 초기 상태
    initial_account = client.get_account_info()
    initial_balance = initial_account.total_balance
    initial_position = client.get_position_by_symbol("BTCUSDT")

    if initial_position:
        initial_size = initial_position.size
        print(f"\n[초기 상태]")
        print(f"잔액: ${initial_balance:,.2f}")
        print(f"포지션: {initial_size:.3f} BTC")
    else:
        initial_size = 0
        print(f"\n[초기 상태]")
        print(f"잔액: ${initial_balance:,.2f}")
        print("포지션: 없음")

    last_order_count = 0
    start_time = datetime.now()

    print("\n모니터링 중... (Ctrl+C로 종료)")
    print("-"*60)

    while True:
        try:
            # 10초마다 확인
            time.sleep(10)

            # 계좌 정보 업데이트
            account = client.get_account_info()
            current_balance = account.total_balance
            pnl = current_balance - initial_balance

            # 포지션 확인
            position = client.get_position_by_symbol("BTCUSDT")

            if position and position.size != initial_size:
                # 포지션 변경 감지
                change = position.size - initial_size
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 포지션 변경!")
                print(f"  변화: {change:+.3f} BTC")
                print(f"  현재: {position.size:.3f} BTC @ ${position.entry_price:,.2f}")
                print(f"  손익: ${position.unrealized_pnl:+.2f}")
                initial_size = position.size

            # 미체결 주문 확인
            open_orders = client.get_open_orders("BTCUSDT")
            if len(open_orders) != last_order_count:
                if open_orders:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 미체결 주문: {len(open_orders)}개")
                    for order in open_orders[:3]:  # 최대 3개만 표시
                        print(f"  - {order.side} {order.quantity:.3f} BTC")
                last_order_count = len(open_orders)

            # 1분마다 상태 업데이트
            elapsed = (datetime.now() - start_time).seconds
            if elapsed % 60 == 0 and elapsed > 0:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 상태 업데이트")
                print(f"  잔액: ${current_balance:,.2f}")
                print(f"  총 손익: ${pnl:+.2f}")
                print(f"  수익률: {(pnl/initial_balance)*100:+.2f}%")

        except KeyboardInterrupt:
            print("\n\n모니터링 종료")
            break
        except Exception as e:
            print(f"오류: {e}")
            time.sleep(5)

    # 최종 결과
    print("\n" + "="*60)
    print("최종 결과")
    print(f"초기 잔액: ${initial_balance:,.2f}")
    print(f"최종 잔액: ${current_balance:,.2f}")
    print(f"총 손익: ${pnl:+.2f}")
    print(f"수익률: {(pnl/initial_balance)*100:+.2f}%")
    print("="*60)

if __name__ == "__main__":
    monitor_new_trades()