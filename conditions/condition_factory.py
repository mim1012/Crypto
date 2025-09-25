"""
조건 팩토리 모듈

이 모듈은 다양한 거래 조건을 생성하는 팩토리를 제공합니다.
"""

from typing import Dict, Any
from conditions.base_condition import BaseCondition
from utils.logger import get_logger
from core.models import Signal, SignalType

logger = get_logger(__name__)


class MACondition(BaseCondition):
    """이동평균선 크로스 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.short_period = params.get("short_period", 20)
        self.long_period = params.get("long_period", 50)
        self.condition_type = params.get("condition_type", "종가기준 상향돌파")
        name = f"MA Cross ({self.short_period}/{self.long_period})"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """조건 평가"""
        import logging
        logger = logging.getLogger("conditions.ma_cross")

        # MA 계산 로직
        if not market_data or not hasattr(market_data, 'close_prices'):
            logger.warning("[MA] 시장 데이터 없음")
            return None

        if len(market_data.close_prices) < self.long_period:
            logger.debug(f"[MA] 데이터 부족: {len(market_data.close_prices)}개 < {self.long_period}개 필요")
            return None

        # 단기/장기 이동평균 계산
        short_ma = sum(market_data.close_prices[-self.short_period:]) / self.short_period
        long_ma = sum(market_data.close_prices[-self.long_period:]) / self.long_period
        current_price = market_data.current_price

        # 크로스 판단
        cross_ratio = (short_ma - long_ma) / long_ma * 100
        logger.info(f"[MA] 현재가: ${current_price:,.2f}, 단기MA: ${short_ma:,.2f}, 장기MA: ${long_ma:,.2f}, 차이: {cross_ratio:.2f}%")

        # 조건별 신호 생성
        if self.condition_type == "종가기준 상향돌파":
            if short_ma > long_ma and cross_ratio > 0.1:  # 0.1% 이상 차이
                logger.info(f"[MA] ✓ 진입 신호! 단기MA > 장기MA (차이: {cross_ratio:.2f}%)")
                return Signal(
                    type=SignalType.BUY,
                    symbol=market_data.symbol,
                    price=current_price,
                    confidence=min(abs(cross_ratio) / 10, 1.0),
                    source="MA Cross",
                    metadata={"reason": f"MA 상향돌파 ({cross_ratio:.2f}%)"}
                )
            else:
                logger.debug(f"[MA] X 조건 미충족: 상향돌파 실패 (차이: {cross_ratio:.2f}%)")
        elif self.condition_type == "종가기준 하향돌파":
            if short_ma < long_ma and cross_ratio < -0.1:
                logger.info(f"[MA] ✓ 진입 신호! 단기MA < 장기MA (차이: {cross_ratio:.2f}%)")
                return Signal(
                    type=SignalType.SELL,
                    symbol=market_data.symbol,
                    price=current_price,
                    confidence=min(abs(cross_ratio) / 10, 1.0),
                    source="MA Cross",
                    metadata={"reason": f"MA 하향돌파 ({cross_ratio:.2f}%)"}
                )
            else:
                logger.debug(f"[MA] X 조건 미충족: 하향돌파 실패 (차이: {cross_ratio:.2f}%)")

        return None


class RSICondition(BaseCondition):
    """RSI 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.period = params.get("period", 14)
        self.oversold = params.get("oversold", 30)
        self.overbought = params.get("overbought", 70)
        name = f"RSI ({self.period})"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """조건 평가"""
        # 실제 구현은 market_data에서 RSI 계산
        return None


class BollingerBandsCondition(BaseCondition):
    """볼린저 밴드 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.period = params.get("period", 20)
        self.std_dev = params.get("std_dev", 2.0)
        name = f"Bollinger Bands ({self.period}, {self.std_dev}σ)"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """조건 평가"""
        # 실제 구현은 market_data에서 볼린저 밴드 계산
        return None


class VolumeSpikeCondition(BaseCondition):
    """거래량 급증 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.period = params.get("period", 20)
        self.multiplier = params.get("multiplier", 2.0)
        name = f"Volume Spike ({self.multiplier}x)"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """조건 평가"""
        # 실제 구현은 market_data에서 거래량 분석
        return None


class FundingRateCondition(BaseCondition):
    """펀딩 비율 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.threshold = params.get("threshold", 0.01)  # 1%
        name = f"Funding Rate (>{self.threshold*100}%)"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """조건 평가"""
        # 실제 구현은 market_data에서 펀딩 비율 확인
        return None


class PriceChannelCondition(BaseCondition):
    """Price Channel 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.period = params.get("period", 20)
        self.condition_type = params.get("condition_type", "상단 매수")
        name = f"Price Channel ({self.period})"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """조건 평가"""
        import logging
        logger = logging.getLogger("conditions.price_channel")

        # PC 계산 로직
        if not market_data or not hasattr(market_data, 'high_prices'):
            logger.warning("[PC] 시장 데이터 없음")
            return None

        if len(market_data.high_prices) < self.period:
            logger.debug(f"[PC] 데이터 부족: {len(market_data.high_prices)}개 < {self.period}개 필요")
            return None

        # Price Channel 상단/하단 계산
        pc_upper = max(market_data.high_prices[-self.period:])
        pc_lower = min(market_data.low_prices[-self.period:])
        current_price = market_data.current_price
        channel_width = pc_upper - pc_lower

        # 현재 가격 위치 계산 (0% = 하단, 100% = 상단)
        position_in_channel = ((current_price - pc_lower) / channel_width * 100) if channel_width > 0 else 50

        logger.info(f"[PC] 현재가: ${current_price:,.2f}, 상단: ${pc_upper:,.2f}, 하단: ${pc_lower:,.2f}, 위치: {position_in_channel:.1f}%")

        # 조건별 신호 생성
        if self.condition_type == "상단 매수":
            distance_to_upper = (pc_upper - current_price) / current_price * 100
            if current_price >= pc_upper * 0.995:  # 상단선 0.5% 이내 접근
                logger.info(f"[PC] ✓ 진입 신호! 상단선 돌파 (거리: {distance_to_upper:.2f}%)")
                return Signal(
                    type=SignalType.BUY,
                    symbol=market_data.symbol,
                    price=current_price,
                    confidence=min(position_in_channel / 100, 1.0),
                    source="Price Channel",
                    metadata={"reason": f"PC 상단 돌파", "position": position_in_channel}
                )
            else:
                logger.debug(f"[PC] X 조건 미충족: 상단 미도달 (거리: {distance_to_upper:.2f}%)")
        elif self.condition_type == "하단 매도":
            distance_to_lower = (current_price - pc_lower) / current_price * 100
            if current_price <= pc_lower * 1.005:  # 하단선 0.5% 이내 접근
                logger.info(f"[PC] ✓ 진입 신호! 하단선 돌파 (거리: {distance_to_lower:.2f}%)")
                return Signal(
                    type=SignalType.SELL,
                    symbol=market_data.symbol,
                    price=current_price,
                    confidence=min((100 - position_in_channel) / 100, 1.0),
                    source="Price Channel",
                    metadata={"reason": f"PC 하단 돌파", "position": position_in_channel}
                )
            else:
                logger.debug(f"[PC] X 조간 미충족: 하단 미도달 (거리: {distance_to_lower:.2f}%)")

        return None


class OrderbookWatchCondition(BaseCondition):
    """호가 감시 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.up_ticks = params.get("up_ticks", 0)
        self.down_ticks = params.get("down_ticks", 0)
        self.immediate_entry = params.get("immediate_entry", False)
        name = f"Orderbook Watch (↑{self.up_ticks}/↓{self.down_ticks})"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """조건 평가"""
        # 실제 구현은 market_data에서 호가 분석
        return None


class CandleStateCondition(BaseCondition):
    """캔들 상태 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.period = params.get("period", 1)
        self.condition_type = params.get("condition_type", "양봉")
        name = f"Candle State ({self.period}분봉 {self.condition_type})"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """조건 평가"""
        # 실제 구현은 market_data에서 캔들 상태 분석
        return None


class TickBasedCondition(BaseCondition):
    """틱 기반 추가 진입 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.up_ticks = params.get("up_ticks", 5)
        self.down_ticks = params.get("down_ticks", 5)
        self.additional_ratio = params.get("additional_ratio", 50)
        name = f"Tick Based (↑{self.up_ticks}/↓{self.down_ticks}, {self.additional_ratio}%)"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """조건 평가"""
        # 실제 구현은 market_data에서 틱 데이터 분석
        return None


class ConditionFactory:
    """조건 팩토리"""

    # 조건 타입 매핑
    CONDITION_CLASSES = {
        "ma_cross": MACondition,
        "rsi": RSICondition,
        "bollinger_bands": BollingerBandsCondition,
        "volume_spike": VolumeSpikeCondition,
        "funding_rate": FundingRateCondition,
        "price_channel": PriceChannelCondition,
        "orderbook_watch": OrderbookWatchCondition,
        "candle_state": CandleStateCondition,
        "tick_based": TickBasedCondition,
    }

    @classmethod
    def create_condition(cls, config: Dict[str, Any]) -> BaseCondition:
        """조건 생성

        Args:
            config: 조건 설정
                - type: 조건 타입 (ma_cross, rsi, bollinger_bands, etc.)
                - enabled: 활성화 여부
                - params: 조건별 파라미터

        Returns:
            생성된 조건 인스턴스
        """
        condition_type = config.get("type")

        if not condition_type:
            raise ValueError("조건 타입이 지정되지 않았습니다")

        condition_class = cls.CONDITION_CLASSES.get(condition_type)

        if not condition_class:
            raise ValueError(f"지원하지 않는 조건 타입: {condition_type}")

        try:
            condition = condition_class(config)
            logger.info(f"조건 생성 완료: {condition.get_name()}")
            return condition

        except Exception as e:
            logger.error(f"조건 생성 실패: {condition_type} - {e}")
            raise