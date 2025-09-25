"""
호가 기반 청산 조건 구현
매수/매도 호가 불균형을 감지하여 청산
"""
from typing import Optional, Dict, Any
from conditions.base_condition import BaseCondition
import logging

class OrderbookExitCondition(BaseCondition):
    """호가 기반 청산 조건"""

    def __init__(self, name: str = "Orderbook Exit", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)

        # 호가 설정
        self.imbalance_ratio = self.config.get('imbalance_ratio', 2.0)  # 불균형 비율
        self.depth_levels = self.config.get('depth_levels', 5)  # 분석할 호가 깊이
        self.min_volume = self.config.get('min_volume', 10000)  # 최소 거래량 (USDT)
        self.consecutive_signals = self.config.get('consecutive_signals', 3)  # 연속 신호 횟수

        # LONG/SHORT 포지션별 설정
        self.long_exit_on_sell_pressure = self.config.get('long_exit_on_sell_pressure', True)
        self.short_exit_on_buy_pressure = self.config.get('short_exit_on_buy_pressure', True)

        # 상태 추적
        self.signal_count = 0
        self.last_imbalance = 0

        self.logger = logging.getLogger(__name__)

    def evaluate(self, market_data, position=None) -> bool:
        """호가 청산 조건 평가

        Args:
            market_data: 시장 데이터 (orderbook 포함)
            position: 현재 포지션

        Returns:
            청산 신호 여부
        """
        if not position or position.size == 0:
            return False

        # 호가 데이터 확인
        orderbook = getattr(market_data, 'orderbook', None)
        if not orderbook:
            return False

        # 호가 불균형 계산
        bid_volume = self._calculate_volume(orderbook.get('bids', []), self.depth_levels)
        ask_volume = self._calculate_volume(orderbook.get('asks', []), self.depth_levels)

        if bid_volume == 0 or ask_volume == 0:
            return False

        # 불균형 비율 계산
        if position.side == "LONG":
            # LONG 포지션: 매도 압력 확인
            if self.long_exit_on_sell_pressure:
                imbalance = ask_volume / bid_volume  # 매도량이 매수량보다 많으면 > 1

                # 매도 압력이 강한 경우
                if imbalance >= self.imbalance_ratio:
                    self.signal_count += 1
                    self.logger.debug(f"매도 압력 감지: {imbalance:.2f}x (신호 {self.signal_count}/{self.consecutive_signals})")

                    # 연속 신호 확인
                    if self.signal_count >= self.consecutive_signals:
                        self.logger.warning(f"호가 청산 신호 (LONG): 강한 매도 압력 {imbalance:.2f}x")
                        self._reset()
                        return True
                else:
                    # 압력이 약해지면 카운트 리셋
                    if self.signal_count > 0:
                        self.signal_count -= 1

        elif position.side == "SHORT":
            # SHORT 포지션: 매수 압력 확인
            if self.short_exit_on_buy_pressure:
                imbalance = bid_volume / ask_volume  # 매수량이 매도량보다 많으면 > 1

                # 매수 압력이 강한 경우
                if imbalance >= self.imbalance_ratio:
                    self.signal_count += 1
                    self.logger.debug(f"매수 압력 감지: {imbalance:.2f}x (신호 {self.signal_count}/{self.consecutive_signals})")

                    # 연속 신호 확인
                    if self.signal_count >= self.consecutive_signals:
                        self.logger.warning(f"호가 청산 신호 (SHORT): 강한 매수 압력 {imbalance:.2f}x")
                        self._reset()
                        return True
                else:
                    # 압력이 약해지면 카운트 리셋
                    if self.signal_count > 0:
                        self.signal_count -= 1

        self.last_imbalance = imbalance
        return False

    def _calculate_volume(self, orders: list, depth: int) -> float:
        """호가 거래량 계산

        Args:
            orders: 호가 리스트 [[price, quantity], ...]
            depth: 분석할 호가 깊이

        Returns:
            총 거래량 (USDT)
        """
        total_volume = 0
        for i, order in enumerate(orders[:depth]):
            if len(order) >= 2:
                price = float(order[0])
                quantity = float(order[1])
                volume = price * quantity
                total_volume += volume

        return total_volume

    def _reset(self):
        """상태 초기화"""
        self.signal_count = 0
        self.last_imbalance = 0

    def get_info(self) -> Dict[str, Any]:
        """조건 정보 반환"""
        return {
            "name": self.name,
            "type": "Orderbook Exit",
            "imbalance_ratio": self.imbalance_ratio,
            "depth_levels": self.depth_levels,
            "signal_count": f"{self.signal_count}/{self.consecutive_signals}",
            "last_imbalance": f"{self.last_imbalance:.2f}x" if self.last_imbalance > 0 else "N/A"
        }