"""
포지션 일부 청산
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.binance.futures_client import BinanceFuturesClient
from api.base_api import APICredentials, OrderRequest, OrderSide, OrderType
from config.settings_manager import SettingsManager

def close_partial_position():
    """포지션 일부 청산"""

    print("="*60)
    print("포지션 일부 청산")
    print("="*60)

    # API 클라이언트 초기화
    settings_manager = SettingsManager()
    exchange_config = settings_manager.get_exchange_config("binance")

    credentials = APICredentials(
        api_key=exchange_config.api_key,
        secret_key=exchange_config.api_secret,
        testnet=exchange_config.testnet
    )

    client = BinanceFuturesClient(credentials)

    # 현재 포지션 확인
    print("\n[현재 포지션]")
    positions = client.get_positions()

    btc_position = None
    for pos in positions:
        if pos.symbol == "BTCUSDT" and pos.size > 0:
            btc_position = pos
            print(f"심볼: {pos.symbol}")
            print(f"방향: {pos.side}")
            print(f"크기: {pos.size:.3f} BTC")
            print(f"진입가: ${pos.entry_price:,.2f}")
            print(f"현재가: ${pos.mark_price:,.2f}")
            print(f"미실현 PnL: ${pos.unrealized_pnl:,.2f}")

    if not btc_position:
        print("활성 포지션이 없습니다.")
        return

    # 90% 청산 (0.1 BTC 정도만 남기고 청산)
    close_quantity = btc_position.size - 0.1

    if close_quantity <= 0:
        print("청산할 수량이 충분하지 않습니다.")
        return

    print(f"\n[청산 계획]")
    print(f"청산할 수량: {close_quantity:.3f} BTC")
    print(f"남길 수량: 0.1 BTC")

    # 청산 주문
    try:
        # LONG 포지션이므로 SELL로 청산
        close_order = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.SELL if btc_position.side == "LONG" else OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=close_quantity,
            reduce_only=True
        )

        print("\n청산 주문 실행 중...")
        result = client.place_order(close_order)

        if result:
            print("청산 완료!")
            print(f"주문 ID: {result.order_id}")
            print(f"체결 수량: {result.filled_quantity:.3f} BTC")

            # 잔고 확인
            import time
            time.sleep(2)

            account = client.get_account_info()
            print(f"\n[청산 후 계좌]")
            print(f"총 잔액: ${account.total_balance:,.2f}")
            print(f"가용 잔액: ${account.available_balance:,.2f}")

    except Exception as e:
        print(f"청산 오류: {e}")

    print("="*60)

if __name__ == "__main__":
    close_partial_position()