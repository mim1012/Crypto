"""
이동평균 진입 조건 모듈

이 모듈은 이동평균선 기반 진입 조건을 구현합니다.
"""

from typing import Optional, Dict, Any
from core.models import MarketData, Signal, Position, SignalType
from conditions.base_condition import EntryCondition
from utils.logger import get_logger

logger = get_logger(__name__)


class MovingAverageCondition(EntryCondition):
    """이동평균 진입 조건"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("이동평균 조건", config)
        
        # 이동평균 설정
        self.period = config.get("period", 20)
        self.condition_type = config.get("condition_type", "close_above")  # close_above, close_below, open_above, open_below
        self.signal_type = config.get("signal_type", "BUY")
        
        # 추가 설정
        self.min_data_points = max(self.period, 4)  # 최소 데이터 포인트
        self.confirmation_candles = config.get("confirmation_candles", 1)  # 확인 캔들 수
        
        logger.info(f"이동평균 조건 초기화: 기간={self.period}, 타입={self.condition_type}")
    
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """이동평균 조건 평가"""
        try:
            # 기본 검증
            if not self.is_active():
                return None
            
            if not self._validate_market_data(market_data):
                return None
            
            # 데이터 충분성 검증
            if len(market_data.close_prices) < self.min_data_points:
                logger.debug(f"{self.name}: 데이터 부족 (필요: {self.min_data_points}, 현재: {len(market_data.close_prices)})")
                return None
            
            # 이동평균 계산
            ma_value = self._calculate_moving_average(market_data.close_prices)
            if ma_value is None:
                return None
            
            # 조건 평가
            signal = self._evaluate_condition(market_data, ma_value)
            
            # 평가 통계 업데이트
            self._update_evaluation_stats(signal)
            
            if signal:
                logger.info(f"{self.name}: 신호 생성 - {signal.type.value} at {signal.price}")
            
            return signal
            
        except Exception as e:
            logger.error(f"{self.name} 평가 오류: {e}")
            return None
    
    def _calculate_moving_average(self, close_prices: list) -> Optional[float]:
        """이동평균 계산"""
        try:
            if len(close_prices) < self.period:
                return None
            
            # 최근 4개 봉의 종가 평균 (PRD 요구사항)
            recent_prices = close_prices[-4:]
            ma_value = sum(recent_prices) / len(recent_prices)
            
            logger.debug(f"{self.name}: MA({self.period}) = {ma_value:.4f}")
            return ma_value
            
        except Exception as e:
            logger.error(f"이동평균 계산 오류: {e}")
            return None
    
    def _evaluate_condition(self, market_data: MarketData, ma_value: float) -> Optional[Signal]:
        """조건 평가 로직"""
        current_price = market_data.current_price
        open_price = market_data.close_prices[-1] if market_data.close_prices else current_price
        
        # 조건별 평가
        condition_met = False
        signal_type = None
        confidence = 0.0
        
        if self.condition_type == "close_above":
            # 현재가 > 이동평균 → 매수 신호
            if current_price > ma_value:
                condition_met = True
                signal_type = SignalType.BUY
                confidence = self._calculate_confidence(current_price, ma_value, "above")
        
        elif self.condition_type == "close_below":
            # 현재가 < 이동평균 → 매도 신호
            if current_price < ma_value:
                condition_met = True
                signal_type = SignalType.SELL
                confidence = self._calculate_confidence(current_price, ma_value, "below")
        
        elif self.condition_type == "open_above":
            # 시가 > 이동평균 → 매수 신호
            if open_price > ma_value:
                condition_met = True
                signal_type = SignalType.BUY
                confidence = self._calculate_confidence(open_price, ma_value, "above")
        
        elif self.condition_type == "open_below":
            # 시가 < 이동평균 → 매도 신호
            if open_price < ma_value:
                condition_met = True
                signal_type = SignalType.SELL
                confidence = self._calculate_confidence(open_price, ma_value, "below")
        
        # 신호 생성
        if condition_met and confidence >= self.confidence_threshold:
            metadata = {
                "ma_value": ma_value,
                "price_vs_ma": current_price - ma_value,
                "condition_type": self.condition_type,
                "period": self.period
            }
            
            return self._create_signal(
                market_data=market_data,
                signal_type=signal_type.value,
                confidence=confidence,
                metadata=metadata
            )
        
        return None
    
    def _calculate_confidence(self, price: float, ma_value: float, direction: str) -> float:
        """신뢰도 계산"""
        try:
            # 가격과 이동평균의 차이를 기반으로 신뢰도 계산
            price_diff = abs(price - ma_value)
            percentage_diff = (price_diff / ma_value) * 100
            
            # 기본 신뢰도 (차이가 클수록 높음)
            base_confidence = min(percentage_diff / 2.0, 0.8)  # 최대 80%
            
            # 방향성 보정
            if direction == "above" and price > ma_value:
                base_confidence += 0.1
            elif direction == "below" and price < ma_value:
                base_confidence += 0.1
            
            # 최종 신뢰도 (0.0 ~ 1.0)
            confidence = max(0.0, min(1.0, base_confidence))
            
            logger.debug(f"{self.name}: 신뢰도 계산 - 가격차이: {percentage_diff:.2f}%, 신뢰도: {confidence:.2f}")
            return confidence
            
        except Exception as e:
            logger.error(f"신뢰도 계산 오류: {e}")
            return 0.0
    
    def get_current_ma_value(self, market_data: MarketData) -> Optional[float]:
        """현재 이동평균값 반환 (GUI 표시용)"""
        if not market_data or len(market_data.close_prices) < self.period:
            return None
        
        return self._calculate_moving_average(market_data.close_prices)
    
    def get_signal_strength(self, market_data: MarketData) -> Dict[str, Any]:
        """신호 강도 정보 반환 (GUI 표시용)"""
        ma_value = self.get_current_ma_value(market_data)
        if not ma_value:
            return {"strength": 0, "direction": "neutral", "ma_value": None}
        
        current_price = market_data.current_price
        price_diff = current_price - ma_value
        percentage_diff = (price_diff / ma_value) * 100
        
        # 신호 방향
        if percentage_diff > 0.1:
            direction = "bullish"
        elif percentage_diff < -0.1:
            direction = "bearish"
        else:
            direction = "neutral"
        
        # 신호 강도 (0-100)
        strength = min(abs(percentage_diff) * 10, 100)
        
        return {
            "strength": strength,
            "direction": direction,
            "ma_value": ma_value,
            "price_diff": price_diff,
            "percentage_diff": percentage_diff
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """설정 업데이트"""
        super().update_config(new_config)
        
        # 이동평균 특화 설정 업데이트
        self.period = self.config.get("period", self.period)
        self.condition_type = self.config.get("condition_type", self.condition_type)
        self.signal_type = self.config.get("signal_type", self.signal_type)
        self.min_data_points = max(self.period, 4)
        
        logger.info(f"{self.name} 설정 업데이트: 기간={self.period}, 타입={self.condition_type}")
    
    def get_status(self) -> Dict[str, Any]:
        """상태 정보 반환"""
        status = super().get_status()
        status.update({
            "period": self.period,
            "condition_type": self.condition_type,
            "signal_type": self.signal_type,
            "min_data_points": self.min_data_points
        })
        return status
    
    def __str__(self) -> str:
        """문자열 표현"""
        return f"이동평균 조건 (기간: {self.period}, 타입: {self.condition_type})"


class MultiTimeframeMACondition(EntryCondition):
    """다중 시간대 이동평균 조건"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("다중시간대 이동평균 조건", config)
        
        # 다중 시간대 설정
        self.short_period = config.get("short_period", 10)
        self.long_period = config.get("long_period", 20)
        self.signal_type = config.get("signal_type", "BUY")
        
        logger.info(f"다중시간대 이동평균 조건 초기화: 단기={self.short_period}, 장기={self.long_period}")
    
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """다중 시간대 이동평균 조건 평가"""
        try:
            if not self.is_active() or not self._validate_market_data(market_data):
                return None
            
            # 데이터 충분성 검증
            if len(market_data.close_prices) < self.long_period:
                return None
            
            # 단기/장기 이동평균 계산
            short_ma = self._calculate_ma(market_data.close_prices, self.short_period)
            long_ma = self._calculate_ma(market_data.close_prices, self.long_period)
            
            if short_ma is None or long_ma is None:
                return None
            
            # 골든크로스/데드크로스 확인
            signal = self._check_crossover(market_data, short_ma, long_ma)
            
            self._update_evaluation_stats(signal)
            return signal
            
        except Exception as e:
            logger.error(f"{self.name} 평가 오류: {e}")
            return None
    
    def _calculate_ma(self, prices: list, period: int) -> Optional[float]:
        """이동평균 계산"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def _check_crossover(self, market_data: MarketData, short_ma: float, long_ma: float) -> Optional[Signal]:
        """크로스오버 확인"""
        current_price = market_data.current_price
        
        # 골든크로스 (단기 > 장기) → 매수 신호
        if short_ma > long_ma:
            confidence = self._calculate_crossover_confidence(short_ma, long_ma, "golden")
            if confidence >= self.confidence_threshold:
                return self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.BUY.value,
                    confidence=confidence,
                    metadata={
                        "short_ma": short_ma,
                        "long_ma": long_ma,
                        "crossover_type": "golden_cross"
                    }
                )
        
        # 데드크로스 (단기 < 장기) → 매도 신호
        elif short_ma < long_ma:
            confidence = self._calculate_crossover_confidence(short_ma, long_ma, "dead")
            if confidence >= self.confidence_threshold:
                return self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.SELL.value,
                    confidence=confidence,
                    metadata={
                        "short_ma": short_ma,
                        "long_ma": long_ma,
                        "crossover_type": "dead_cross"
                    }
                )
        
        return None
    
    def _calculate_crossover_confidence(self, short_ma: float, long_ma: float, cross_type: str) -> float:
        """크로스오버 신뢰도 계산"""
        try:
            ma_diff = abs(short_ma - long_ma)
            percentage_diff = (ma_diff / long_ma) * 100
            
            # 차이가 클수록 신뢰도 높음
            confidence = min(percentage_diff / 1.0, 0.9)  # 최대 90%
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"크로스오버 신뢰도 계산 오류: {e}")
            return 0.0
