"""
긴급 청산 기능 구현 및 테스트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.binance.futures_client import BinanceFuturesClient
from api.base_api import APICredentials
from config.settings_manager import SettingsManager
from datetime import datetime
import time

class EmergencyCloseManager:
    """긴급 청산 관리자"""

    def __init__(self):
        self.settings_manager = SettingsManager()
        self.binance_client = None
        self.bybit_client = None
        self._init_clients()

    def _init_clients(self):
        """API 클라이언트 초기화"""
        # Binance 클라이언트
        binance_config = self.settings_manager.get_exchange_config("binance")
        if binance_config.api_key and binance_config.api_secret:
            credentials = APICredentials(
                api_key=binance_config.api_key,
                secret_key=binance_config.api_secret,
                testnet=binance_config.testnet
            )
            self.binance_client = BinanceFuturesClient(credentials)
            print(f"Binance 클라이언트 초기화 완료")

    def close_all_positions(self, confirm=False):
        """모든 포지션 긴급 청산"""
        if not confirm:
            print("경고: 긴급 청산을 실행하려면 confirm=True로 설정하세요")
            return False

        print("\n" + "="*60)
        print("[긴급] 모든 포지션 긴급 청산 시작")
        print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        total_closed = 0
        errors = []

        # Binance 포지션 청산
        if self.binance_client:
            try:
                positions = self.binance_client.get_positions()
                active_positions = [p for p in positions if p.size != 0]

                if active_positions:
                    print(f"\n[Binance] {len(active_positions)}개 포지션 발견")

                    for pos in active_positions:
                        try:
                            print(f"청산 중: {pos.symbol} {pos.size:.3f}")

                            # 시장가로 반대 포지션 생성하여 청산
                            side = "SELL" if pos.side == "LONG" else "BUY"
                            order = self.binance_client.place_market_order(
                                symbol=pos.symbol,
                                side=side,
                                quantity=abs(pos.size),
                                reduce_only=True
                            )

                            if order:
                                print(f"✓ {pos.symbol} 청산 완료")
                                total_closed += 1
                            else:
                                print(f"✗ {pos.symbol} 청산 실패")
                                errors.append(f"{pos.symbol} 청산 실패")

                        except Exception as e:
                            error_msg = f"{pos.symbol} 청산 오류: {str(e)}"
                            print(f"✗ {error_msg}")
                            errors.append(error_msg)

                        time.sleep(0.5)  # API 제한 방지
                else:
                    print("[Binance] 활성 포지션 없음")

            except Exception as e:
                error_msg = f"Binance 포지션 조회 실패: {str(e)}"
                print(f"✗ {error_msg}")
                errors.append(error_msg)

        # 결과 요약
        print("\n" + "="*60)
        print("긴급 청산 완료")
        print(f"청산된 포지션: {total_closed}개")
        if errors:
            print(f"오류 발생: {len(errors)}건")
            for error in errors:
                print(f"  - {error}")
        print("="*60)

        return total_closed > 0 or len(errors) == 0

    def get_active_positions_summary(self):
        """활성 포지션 요약 조회"""
        summary = {
            "total_positions": 0,
            "total_value": 0,
            "total_pnl": 0,
            "positions": []
        }

        if self.binance_client:
            try:
                positions = self.binance_client.get_positions()
                for pos in positions:
                    if pos.size != 0:
                        summary["total_positions"] += 1
                        summary["total_value"] += abs(pos.size * pos.current_price)
                        summary["total_pnl"] += pos.unrealized_pnl
                        summary["positions"].append({
                            "exchange": "Binance",
                            "symbol": pos.symbol,
                            "size": pos.size,
                            "value": abs(pos.size * pos.current_price),
                            "pnl": pos.unrealized_pnl
                        })
            except Exception as e:
                print(f"Binance 포지션 조회 실패: {e}")

        return summary


def test_emergency_close():
    """긴급 청산 테스트"""
    manager = EmergencyCloseManager()

    # 현재 포지션 확인
    print("\n[현재 포지션 확인]")
    summary = manager.get_active_positions_summary()

    print(f"총 포지션: {summary['total_positions']}개")
    print(f"총 가치: ${summary['total_value']:,.2f}")
    print(f"총 손익: ${summary['total_pnl']:+.2f}")

    if summary['positions']:
        print("\n포지션 상세:")
        for pos in summary['positions']:
            print(f"  - {pos['exchange']} {pos['symbol']}: ${pos['value']:,.2f} (PnL: ${pos['pnl']:+.2f})")

    # 긴급 청산 시뮬레이션 (실제 실행하려면 confirm=True)
    print("\n[긴급 청산 시뮬레이션]")
    print("실제로 청산하려면 close_all_positions(confirm=True) 실행")

    # 실제 청산 예시 (주의!)
    # manager.close_all_positions(confirm=True)


if __name__ == "__main__":
    test_emergency_close()