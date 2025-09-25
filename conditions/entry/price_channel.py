"""
Price Channel 진입 조건 모듈

이 모듈은 Price Channel 돌파 기반 진입 조건을 구현합니다.
"""

from typing import Optional, Dict, Any, Tuple
from core.models import MarketData, Signal, Position, SignalType
from conditions.base_condition import EntryCondition
from utils.logger import get_logger

logger = get_logger(__name__)


class PriceChannelCondition(EntryCondition):
    """Price Channel 진입 조건"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Price Channel 조건", config)
        
        # Price Channel 설정
        self.period = config.get("period", 20)
        self.upper_breakout = config.get("upper_breakout", "none")  # none, buy, sell
        self.lower_breakout = config.get("lower_breakout", "none")  # none, buy, sell
        
        # 돌파 확인 설정
        self.breakout_threshold = config.get("breakout_threshold", 0.001)  # 0.1% 돌파 임계값
        self.confirmation_candles = config.get("confirmation_candles", 1)
        
        # 최소 데이터 포인트
        self.min_data_points = max(self.period, 10)
        
        logger.info(f"Price Channel 조건 초기화: 기간={self.period}, 상단돌파={self.upper_breakout}, 하단돌파={self.lower_breakout}")
    
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """Price Channel 조건 평가"""
        try:
            # 기본 검증
            if not self.is_active():
                return None
            
            if not self._validate_market_data(market_data):
                return None
            
            # 데이터 충분성 검증
            if (len(market_data.high_prices) < self.min_data_points or 
                len(market_data.low_prices) < self.min_data_points):
                logger.debug(f"{self.name}: 데이터 부족")
                return None
            
            # Price Channel 계산
            channel = self._calculate_price_channel(market_data)
            if not channel:
                return None
            
            # 돌파 조건 평가
            signal = self._evaluate_breakout(market_data, channel)
            
            # 평가 통계 업데이트
            self._update_evaluation_stats(signal)
            
            if signal:
                logger.info(f"{self.name}: 신호 생성 - {signal.type.value} at {signal.price}")
            
            return signal
            
        except Exception as e:
            logger.error(f"{self.name} 평가 오류: {e}")
            return None
    
    def _calculate_price_channel(self, market_data: MarketData) -> Optional[Dict[str, float]]:
        """Price Channel 계산"""
        try:
            high_prices = market_data.high_prices[-self.period:]
            low_prices = market_data.low_prices[-self.period:]
            
            if len(high_prices) < self.period or len(low_prices) < self.period:
                return None
            
            upper_line = max(high_prices)
            lower_line = min(low_prices)
            middle_line = (upper_line + lower_line) / 2
            
            channel = {
                "upper": upper_line,
                "lower": lower_line,
                "middle": middle_line,
                "width": upper_line - lower_line,
                "width_percentage": ((upper_line - lower_line) / middle_line) * 100
            }
            
            logger.debug(f"{self.name}: Channel - 상단: {upper_line:.4f}, 하단: {lower_line:.4f}, 폭: {channel['width_percentage']:.2f}%")
            return channel
            
        except Exception as e:
            logger.error(f"Price Channel 계산 오류: {e}")
            return None
    
    def _evaluate_breakout(self, market_data: MarketData, channel: Dict[str, float]) -> Optional[Signal]:
        """돌파 조건 평가"""
        current_price = market_data.current_price
        upper_line = channel["upper"]
        lower_line = channel["lower"]
        
        # 상단선 돌파 확인
        if self.upper_breakout != "none":
            upper_breakout_price = upper_line * (1 + self.breakout_threshold)
            if current_price > upper_breakout_price:
                signal_type = SignalType.BUY if self.upper_breakout == "buy" else SignalType.SELL
                confidence = self._calculate_breakout_confidence(current_price, upper_line, "upper")
                
                if confidence >= self.confidence_threshold:
                    metadata = {
                        "channel": channel,
                        "breakout_type": "upper",
                        "breakout_direction": self.upper_breakout,
                        "breakout_percentage": ((current_price - upper_line) / upper_line) * 100
                    }
                    
                    return self._create_signal(
                        market_data=market_data,
                        signal_type=signal_type.value,
                        confidence=confidence,
                        metadata=metadata
                    )
        
        # 하단선 돌파 확인
        if self.lower_breakout != "none":
            lower_breakout_price = lower_line * (1 - self.breakout_threshold)
            if current_price < lower_breakout_price:
                signal_type = SignalType.BUY if self.lower_breakout == "buy" else SignalType.SELL
                confidence = self._calculate_breakout_confidence(current_price, lower_line, "lower")
                
                if confidence >= self.confidence_threshold:
                    metadata = {
                        "channel": channel,
                        "breakout_type": "lower",
                        "breakout_direction": self.lower_breakout,
                        "breakout_percentage": ((lower_line - current_price) / lower_line) * 100
                    }
                    
                    return self._create_signal(
                        market_data=market_data,
                        signal_type=signal_type.value,
                        confidence=confidence,
                        metadata=metadata
                    )
        
        return None
    
    def _calculate_breakout_confidence(self, current_price: float, line_price: float, breakout_type: str) -> float:
        """돌파 신뢰도 계산"""
        try:
            # 돌파 정도에 따른 신뢰도 계산
            if breakout_type == "upper":
                breakout_percentage = ((current_price - line_price) / line_price) * 100
            else:  # lower
                breakout_percentage = ((line_price - current_price) / line_price) * 100
            
            # 돌파 정도가 클수록 신뢰도 높음
            base_confidence = min(breakout_percentage / 2.0, 0.8)  # 최대 80%
            
            # 최소 신뢰도 보장
            confidence = max(0.3, base_confidence)  # 최소 30%
            
            logger.debug(f"{self.name}: 돌파 신뢰도 - 돌파율: {breakout_percentage:.2f}%, 신뢰도: {confidence:.2f}")
            return min(1.0, confidence)
            
        except Exception as e:
            logger.error(f"돌파 신뢰도 계산 오류: {e}")
            return 0.0
    
    def get_current_channel(self, market_data: MarketData) -> Optional[Dict[str, float]]:
        """현재 Price Channel 정보 반환 (GUI 표시용)"""
        if not market_data:
            return None
        
        return self._calculate_price_channel(market_data)
    
    def get_breakout_status(self, market_data: MarketData) -> Dict[str, Any]:
        """돌파 상태 정보 반환 (GUI 표시용)"""
        channel = self.get_current_channel(market_data)
        if not channel:
            return {"status": "no_data", "channel": None}
        
        current_price = market_data.current_price
        upper_line = channel["upper"]
        lower_line = channel["lower"]
        middle_line = channel["middle"]
        
        # 현재 위치 계산
        if current_price > upper_line:
            position = "above_upper"
            distance_percentage = ((current_price - upper_line) / upper_line) * 100
        elif current_price < lower_line:
            position = "below_lower"
            distance_percentage = ((lower_line - current_price) / lower_line) * 100
        else:
            position = "inside_channel"
            # 채널 내 위치 (0: 하단, 50: 중간, 100: 상단)
            channel_position = ((current_price - lower_line) / (upper_line - lower_line)) * 100
            distance_percentage = abs(channel_position - 50)  # 중간선으로부터의 거리
        
        return {
            "status": position,
            "channel": channel,
            "current_price": current_price,
            "distance_percentage": distance_percentage,
            "channel_position": channel_position if position == "inside_channel" else None
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """설정 업데이트"""
        super().update_config(new_config)
        
        # Price Channel 특화 설정 업데이트
        self.period = self.config.get("period", self.period)
        self.upper_breakout = self.config.get("upper_breakout", self.upper_breakout)
        self.lower_breakout = self.config.get("lower_breakout", self.lower_breakout)
        self.breakout_threshold = self.config.get("breakout_threshold", self.breakout_threshold)
        self.min_data_points = max(self.period, 10)
        
        logger.info(f"{self.name} 설정 업데이트: 기간={self.period}, 상단={self.upper_breakout}, 하단={self.lower_breakout}")
    
    def get_status(self) -> Dict[str, Any]:
        """상태 정보 반환"""
        status = super().get_status()
        status.update({
            "period": self.period,
            "upper_breakout": self.upper_breakout,
            "lower_breakout": self.lower_breakout,
            "breakout_threshold": self.breakout_threshold
        })
        return status
    
    def __str__(self) -> str:
        """문자열 표현"""
        return f"Price Channel 조건 (기간: {self.period}, 상단: {self.upper_breakout}, 하단: {self.lower_breakout})"


class AdaptivePriceChannelCondition(EntryCondition):
    """적응형 Price Channel 조건"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("적응형 Price Channel 조건", config)
        
        # 적응형 설정
        self.base_period = config.get("base_period", 20)
        self.volatility_adjustment = config.get("volatility_adjustment", True)
        self.volume_confirmation = config.get("volume_confirmation", False)
        
        # 변동성 기반 기간 조정
        self.min_period = config.get("min_period", 10)
        self.max_period = config.get("max_period", 50)
        
        logger.info(f"적응형 Price Channel 조건 초기화: 기본기간={self.base_period}")
    
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """적응형 Price Channel 조건 평가"""
        try:
            if not self.is_active() or not self._validate_market_data(market_data):
                return None
            
            # 적응형 기간 계산
            adaptive_period = self._calculate_adaptive_period(market_data)
            
            # 적응형 채널 계산
            channel = self._calculate_adaptive_channel(market_data, adaptive_period)
            if not channel:
                return None
            
            # 돌파 신호 평가
            signal = self._evaluate_adaptive_breakout(market_data, channel, adaptive_period)
            
            self._update_evaluation_stats(signal)
            return signal
            
        except Exception as e:
            logger.error(f"{self.name} 평가 오류: {e}")
            return None
    
    def _calculate_adaptive_period(self, market_data: MarketData) -> int:
        """변동성 기반 적응형 기간 계산"""
        try:
            if not self.volatility_adjustment or len(market_data.close_prices) < 20:
                return self.base_period
            
            # 최근 20개 봉의 변동성 계산
            recent_prices = market_data.close_prices[-20:]
            volatility = self._calculate_volatility(recent_prices)
            
            # 변동성이 높으면 기간 단축, 낮으면 기간 연장
            if volatility > 0.03:  # 3% 이상
                period = max(self.min_period, self.base_period - 5)
            elif volatility < 0.01:  # 1% 이하
                period = min(self.max_period, self.base_period + 10)
            else:
                period = self.base_period
            
            logger.debug(f"{self.name}: 적응형 기간 - 변동성: {volatility:.4f}, 기간: {period}")
            return period
            
        except Exception as e:
            logger.error(f"적응형 기간 계산 오류: {e}")
            return self.base_period
    
    def _calculate_volatility(self, prices: list) -> float:
        """가격 변동성 계산"""
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
        
        # 표준편차 계산
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5
        
        return volatility
    
    def _calculate_adaptive_channel(self, market_data: MarketData, period: int) -> Optional[Dict[str, float]]:
        """적응형 채널 계산"""
        try:
            if (len(market_data.high_prices) < period or 
                len(market_data.low_prices) < period):
                return None
            
            high_prices = market_data.high_prices[-period:]
            low_prices = market_data.low_prices[-period:]
            
            # 기본 채널
            upper_line = max(high_prices)
            lower_line = min(low_prices)
            
            # 볼륨 가중 조정 (옵션)
            if self.volume_confirmation and hasattr(market_data, 'volume') and market_data.volume > 0:
                # 볼륨이 높은 구간의 가격에 더 높은 가중치 부여
                # 실제 구현에서는 볼륨 데이터를 활용한 가중 계산
                pass
            
            middle_line = (upper_line + lower_line) / 2
            
            return {
                "upper": upper_line,
                "lower": lower_line,
                "middle": middle_line,
                "width": upper_line - lower_line,
                "period": period,
                "adaptive": True
            }
            
        except Exception as e:
            logger.error(f"적응형 채널 계산 오류: {e}")
            return None
    
    def _evaluate_adaptive_breakout(self, market_data: MarketData, channel: Dict[str, float], period: int) -> Optional[Signal]:
        """적응형 돌파 평가"""
        current_price = market_data.current_price
        upper_line = channel["upper"]
        lower_line = channel["lower"]
        
        # 동적 임계값 계산 (변동성 기반)
        channel_width = upper_line - lower_line
        dynamic_threshold = min(0.005, (channel_width / channel["middle"]) * 0.1)  # 최대 0.5%
        
        # 상단 돌파
        if current_price > upper_line * (1 + dynamic_threshold):
            confidence = self._calculate_adaptive_confidence(current_price, upper_line, "upper", period)
            if confidence >= self.confidence_threshold:
                return self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.BUY.value,
                    confidence=confidence,
                    metadata={
                        "channel": channel,
                        "breakout_type": "adaptive_upper",
                        "dynamic_threshold": dynamic_threshold,
                        "adaptive_period": period
                    }
                )
        
        # 하단 돌파
        elif current_price < lower_line * (1 - dynamic_threshold):
            confidence = self._calculate_adaptive_confidence(current_price, lower_line, "lower", period)
            if confidence >= self.confidence_threshold:
                return self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.SELL.value,
                    confidence=confidence,
                    metadata={
                        "channel": channel,
                        "breakout_type": "adaptive_lower",
                        "dynamic_threshold": dynamic_threshold,
                        "adaptive_period": period
                    }
                )
        
        return None
    
    def _calculate_adaptive_confidence(self, current_price: float, line_price: float, breakout_type: str, period: int) -> float:
        """적응형 신뢰도 계산"""
        try:
            # 기본 돌파 신뢰도
            if breakout_type == "upper":
                breakout_percentage = ((current_price - line_price) / line_price) * 100
            else:
                breakout_percentage = ((line_price - current_price) / line_price) * 100
            
            base_confidence = min(breakout_percentage / 1.5, 0.8)
            
            # 기간 기반 보정 (짧은 기간일수록 신뢰도 감소)
            period_factor = min(period / self.base_period, 1.2)
            
            confidence = base_confidence * period_factor
            return max(0.2, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"적응형 신뢰도 계산 오류: {e}")
            return 0.0
