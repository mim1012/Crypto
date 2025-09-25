"""
PCT (Price Channel Trailing) 청산 조건 구현
가격 채널을 따라 트레일링 스탑 설정
"""
from typing import Optional, Dict, Any
from conditions.base_condition import BaseCondition
import logging

class PCTExitCondition(BaseCondition):
    """Price Channel Trailing 청산 조건"""

    def __init__(self, name: str = "PCT Exit", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)

        # PCT 설정
        self.channel_period = self.config.get('channel_period', 20)
        self.trailing_offset = self.config.get('trailing_offset', 2.0)  # %
        self.activation_profit = self.config.get('activation_profit', 2.0)  # 활성화 수익률

        # 상태 추적
        self.is_activated = False
        self.highest_channel = None
        self.lowest_channel = None
        self.trailing_stop_price = None

        self.logger = logging.getLogger(__name__)

    def evaluate(self, market_data, position=None) -> bool:
        """PCT 청산 조건 평가

        Args:
            market_data: 시장 데이터
            position: 현재 포지션

        Returns:
            청산 신호 여부
        """
        if not position or position.size == 0:
            return False

        # 가격 채널 계산
        price_channel = market_data.get_price_channel(self.channel_period)
        if not price_channel:
            return False

        upper_channel = price_channel['upper']
        lower_channel = price_channel['lower']
        current_price = market_data.current_price

        # 수익률 계산
        if position.entry_price > 0:
            profit_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        else:
            return False

        # LONG 포지션
        if position.side == "LONG":
            # 활성화 조건: 수익률이 임계값 도달
            if not self.is_activated and profit_pct >= self.activation_profit:
                self.is_activated = True
                self.highest_channel = upper_channel
                self.trailing_stop_price = upper_channel * (1 - self.trailing_offset / 100)
                self.logger.info(f"PCT 활성화: 수익률 {profit_pct:.2f}%, 트레일링 스탑 ${self.trailing_stop_price:.2f}")

            # 트레일링 업데이트
            if self.is_activated:
                if upper_channel > self.highest_channel:
                    self.highest_channel = upper_channel
                    self.trailing_stop_price = upper_channel * (1 - self.trailing_offset / 100)
                    self.logger.debug(f"PCT 업데이트: 새로운 트레일링 스탑 ${self.trailing_stop_price:.2f}")

                # 청산 조건: 현재가가 트레일링 스탑 이하
                if current_price <= self.trailing_stop_price:
                    self.logger.warning(f"PCT 청산 신호: 가격 ${current_price:.2f} <= 트레일링 스탑 ${self.trailing_stop_price:.2f}")
                    self._reset()
                    return True

        # SHORT 포지션
        elif position.side == "SHORT":
            # 활성화 조건: 수익률이 임계값 도달 (SHORT는 가격 하락시 수익)
            profit_pct_short = ((position.entry_price - current_price) / position.entry_price) * 100

            if not self.is_activated and profit_pct_short >= self.activation_profit:
                self.is_activated = True
                self.lowest_channel = lower_channel
                self.trailing_stop_price = lower_channel * (1 + self.trailing_offset / 100)
                self.logger.info(f"PCT 활성화 (SHORT): 수익률 {profit_pct_short:.2f}%, 트레일링 스탑 ${self.trailing_stop_price:.2f}")

            # 트레일링 업데이트
            if self.is_activated:
                if lower_channel < self.lowest_channel:
                    self.lowest_channel = lower_channel
                    self.trailing_stop_price = lower_channel * (1 + self.trailing_offset / 100)
                    self.logger.debug(f"PCT 업데이트 (SHORT): 새로운 트레일링 스탑 ${self.trailing_stop_price:.2f}")

                # 청산 조건: 현재가가 트레일링 스탑 이상
                if current_price >= self.trailing_stop_price:
                    self.logger.warning(f"PCT 청산 신호 (SHORT): 가격 ${current_price:.2f} >= 트레일링 스탑 ${self.trailing_stop_price:.2f}")
                    self._reset()
                    return True

        return False

    def _reset(self):
        """상태 초기화"""
        self.is_activated = False
        self.highest_channel = None
        self.lowest_channel = None
        self.trailing_stop_price = None

    def get_info(self) -> Dict[str, Any]:
        """조건 정보 반환"""
        return {
            "name": self.name,
            "type": "PCT Exit",
            "channel_period": self.channel_period,
            "trailing_offset": f"{self.trailing_offset}%",
            "activation_profit": f"{self.activation_profit}%",
            "is_activated": self.is_activated,
            "trailing_stop": self.trailing_stop_price
        }