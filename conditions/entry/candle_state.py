"""
캔들 상태 진입 조건 모듈

이 모듈은 캔들 상태(양봉/음봉) 기반 진입 조건을 구현합니다.
"""

from typing import Optional, Dict, Any, List
from core.models import MarketData, Signal, Position, SignalType
from conditions.base_condition import EntryCondition
from utils.logger import get_logger

logger = get_logger(__name__)


class CandleStateCondition(EntryCondition):
    """캔들 상태 진입 조건"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("캔들 상태 조건", config)
        
        # 캔들 상태 설정
        self.bullish_signal = config.get("bullish_signal", "none")  # none, buy, sell
        self.bearish_signal = config.get("bearish_signal", "none")  # none, buy, sell
        
        # 캔들 분석 설정
        self.min_body_percentage = config.get("min_body_percentage", 0.1)  # 최소 몸통 크기 (0.1%)
        self.confirmation_time = config.get("confirmation_time", 30)  # 확인 시간 (초)
        
        # 연속 캔들 패턴
        self.consecutive_candles = config.get("consecutive_candles", 1)  # 연속 캔들 수
        self.pattern_memory = []  # 최근 캔들 패턴 기억
        
        logger.info(f"캔들 상태 조건 초기화: 양봉신호={self.bullish_signal}, 음봉신호={self.bearish_signal}")
    
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """캔들 상태 조건 평가"""
        try:
            # 기본 검증
            if not self.is_active():
                return None
            
            if not self._validate_market_data(market_data):
                return None
            
            # 현재 캔들 상태 분석
            candle_state = self._analyze_current_candle(market_data)
            if not candle_state:
                return None
            
            # 패턴 메모리 업데이트
            self._update_pattern_memory(candle_state)
            
            # 신호 평가
            signal = self._evaluate_candle_signal(market_data, candle_state)
            
            # 평가 통계 업데이트
            self._update_evaluation_stats(signal)
            
            if signal:
                logger.info(f"{self.name}: 신호 생성 - {signal.type.value} at {signal.price} (캔들: {candle_state['type']})")
            
            return signal
            
        except Exception as e:
            logger.error(f"{self.name} 평가 오류: {e}")
            return None
    
    def _analyze_current_candle(self, market_data: MarketData) -> Optional[Dict[str, Any]]:
        """현재 캔들 상태 분석"""
        try:
            current_price = market_data.current_price
            
            # 시가 추정 (이전 봉의 종가)
            if len(market_data.close_prices) > 0:
                open_price = market_data.close_prices[-1]
            else:
                # 데이터가 없으면 현재가를 시가로 사용
                open_price = current_price
            
            # 캔들 기본 정보
            price_diff = current_price - open_price
            body_percentage = abs(price_diff / open_price) * 100 if open_price > 0 else 0
            
            # 캔들 타입 결정
            if price_diff > 0:
                candle_type = "bullish"  # 양봉
            elif price_diff < 0:
                candle_type = "bearish"  # 음봉
            else:
                candle_type = "doji"  # 도지
            
            # 캔들 강도 계산
            strength = self._calculate_candle_strength(body_percentage, candle_type)
            
            candle_state = {
                "type": candle_type,
                "open_price": open_price,
                "current_price": current_price,
                "price_diff": price_diff,
                "body_percentage": body_percentage,
                "strength": strength,
                "timestamp": market_data.timestamp
            }
            
            logger.debug(f"{self.name}: 캔들 분석 - 타입: {candle_type}, 몸통: {body_percentage:.2f}%, 강도: {strength:.2f}")
            return candle_state
            
        except Exception as e:
            logger.error(f"캔들 상태 분석 오류: {e}")
            return None
    
    def _calculate_candle_strength(self, body_percentage: float, candle_type: str) -> float:
        """캔들 강도 계산"""
        try:
            # 몸통 크기 기반 강도 계산
            if body_percentage < self.min_body_percentage:
                return 0.0  # 너무 작은 캔들은 강도 0
            
            # 기본 강도 (몸통 크기에 비례)
            base_strength = min(body_percentage / 2.0, 1.0)  # 최대 100%
            
            # 캔들 타입별 보정
            if candle_type == "doji":
                base_strength *= 0.5  # 도지는 강도 감소
            
            return base_strength
            
        except Exception as e:
            logger.error(f"캔들 강도 계산 오류: {e}")
            return 0.0
    
    def _update_pattern_memory(self, candle_state: Dict[str, Any]) -> None:
        """패턴 메모리 업데이트"""
        self.pattern_memory.append(candle_state)
        
        # 최대 메모리 크기 유지 (연속 캔들 수의 2배)
        max_memory = max(self.consecutive_candles * 2, 5)
        if len(self.pattern_memory) > max_memory:
            self.pattern_memory.pop(0)
    
    def _evaluate_candle_signal(self, market_data: MarketData, candle_state: Dict[str, Any]) -> Optional[Signal]:
        """캔들 신호 평가"""
        candle_type = candle_state["type"]
        
        # 연속 캔들 패턴 확인
        if not self._check_consecutive_pattern(candle_type):
            return None
        
        # 양봉 신호
        if candle_type == "bullish" and self.bullish_signal != "none":
            if candle_state["body_percentage"] >= self.min_body_percentage:
                signal_type = SignalType.BUY if self.bullish_signal == "buy" else SignalType.SELL
                confidence = self._calculate_candle_confidence(candle_state, "bullish")
                
                if confidence >= self.confidence_threshold:
                    metadata = {
                        "candle_state": candle_state,
                        "signal_direction": self.bullish_signal,
                        "consecutive_count": self._count_consecutive_candles(candle_type)
                    }
                    
                    return self._create_signal(
                        market_data=market_data,
                        signal_type=signal_type.value,
                        confidence=confidence,
                        metadata=metadata
                    )
        
        # 음봉 신호
        elif candle_type == "bearish" and self.bearish_signal != "none":
            if candle_state["body_percentage"] >= self.min_body_percentage:
                signal_type = SignalType.BUY if self.bearish_signal == "buy" else SignalType.SELL
                confidence = self._calculate_candle_confidence(candle_state, "bearish")
                
                if confidence >= self.confidence_threshold:
                    metadata = {
                        "candle_state": candle_state,
                        "signal_direction": self.bearish_signal,
                        "consecutive_count": self._count_consecutive_candles(candle_type)
                    }
                    
                    return self._create_signal(
                        market_data=market_data,
                        signal_type=signal_type.value,
                        confidence=confidence,
                        metadata=metadata
                    )
        
        return None
    
    def _check_consecutive_pattern(self, current_type: str) -> bool:
        """연속 캔들 패턴 확인"""
        if self.consecutive_candles <= 1:
            return True  # 단일 캔들은 항상 통과
        
        if len(self.pattern_memory) < self.consecutive_candles:
            return False  # 충분한 데이터 없음
        
        # 최근 N개 캔들이 모두 같은 타입인지 확인
        recent_candles = self.pattern_memory[-self.consecutive_candles:]
        return all(candle["type"] == current_type for candle in recent_candles)
    
    def _count_consecutive_candles(self, candle_type: str) -> int:
        """연속 캔들 수 계산"""
        count = 0
        for candle in reversed(self.pattern_memory):
            if candle["type"] == candle_type:
                count += 1
            else:
                break
        return count
    
    def _calculate_candle_confidence(self, candle_state: Dict[str, Any], signal_type: str) -> float:
        """캔들 신뢰도 계산"""
        try:
            # 기본 신뢰도 (몸통 크기 기반)
            base_confidence = min(candle_state["body_percentage"] / 1.0, 0.8)  # 최대 80%
            
            # 연속 캔들 보너스
            consecutive_count = self._count_consecutive_candles(candle_state["type"])
            consecutive_bonus = min(consecutive_count * 0.1, 0.2)  # 최대 20% 보너스
            
            # 캔들 강도 보정
            strength_factor = candle_state["strength"]
            
            # 최종 신뢰도
            confidence = (base_confidence + consecutive_bonus) * strength_factor
            confidence = max(0.2, min(1.0, confidence))  # 20% ~ 100%
            
            logger.debug(f"{self.name}: 캔들 신뢰도 - 기본: {base_confidence:.2f}, 연속: {consecutive_bonus:.2f}, 최종: {confidence:.2f}")
            return confidence
            
        except Exception as e:
            logger.error(f"캔들 신뢰도 계산 오류: {e}")
            return 0.0
    
    def get_current_candle_info(self, market_data: MarketData) -> Dict[str, Any]:
        """현재 캔들 정보 반환 (GUI 표시용)"""
        candle_state = self._analyze_current_candle(market_data)
        if not candle_state:
            return {"status": "no_data"}
        
        consecutive_count = self._count_consecutive_candles(candle_state["type"])
        
        # 신호 상태 판단
        signal_ready = False
        if candle_state["type"] == "bullish" and self.bullish_signal != "none":
            signal_ready = candle_state["body_percentage"] >= self.min_body_percentage
        elif candle_state["type"] == "bearish" and self.bearish_signal != "none":
            signal_ready = candle_state["body_percentage"] >= self.min_body_percentage
        
        return {
            "status": "active",
            "candle_type": candle_state["type"],
            "body_percentage": candle_state["body_percentage"],
            "strength": candle_state["strength"],
            "consecutive_count": consecutive_count,
            "signal_ready": signal_ready,
            "min_body_threshold": self.min_body_percentage
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """설정 업데이트"""
        super().update_config(new_config)
        
        # 캔들 상태 특화 설정 업데이트
        self.bullish_signal = self.config.get("bullish_signal", self.bullish_signal)
        self.bearish_signal = self.config.get("bearish_signal", self.bearish_signal)
        self.min_body_percentage = self.config.get("min_body_percentage", self.min_body_percentage)
        self.consecutive_candles = self.config.get("consecutive_candles", self.consecutive_candles)
        
        logger.info(f"{self.name} 설정 업데이트: 양봉={self.bullish_signal}, 음봉={self.bearish_signal}")
    
    def get_status(self) -> Dict[str, Any]:
        """상태 정보 반환"""
        status = super().get_status()
        status.update({
            "bullish_signal": self.bullish_signal,
            "bearish_signal": self.bearish_signal,
            "min_body_percentage": self.min_body_percentage,
            "consecutive_candles": self.consecutive_candles,
            "pattern_memory_size": len(self.pattern_memory)
        })
        return status
    
    def __str__(self) -> str:
        """문자열 표현"""
        return f"캔들 상태 조건 (양봉: {self.bullish_signal}, 음봉: {self.bearish_signal})"


class AdvancedCandlePatternCondition(EntryCondition):
    """고급 캔들 패턴 조건"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("고급 캔들 패턴 조건", config)
        
        # 고급 패턴 설정
        self.pattern_types = config.get("pattern_types", ["hammer", "doji", "engulfing"])
        self.pattern_sensitivity = config.get("pattern_sensitivity", 0.7)  # 패턴 민감도
        
        # 패턴별 가중치
        self.pattern_weights = config.get("pattern_weights", {
            "hammer": 0.8,
            "doji": 0.6,
            "engulfing": 0.9,
            "shooting_star": 0.7
        })
        
        logger.info(f"고급 캔들 패턴 조건 초기화: 패턴={self.pattern_types}")
    
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """고급 캔들 패턴 조건 평가"""
        try:
            if not self.is_active() or not self._validate_market_data(market_data):
                return None
            
            # 캔들 데이터 충분성 확인
            if len(market_data.close_prices) < 3:
                return None
            
            # 패턴 분석
            detected_patterns = self._detect_patterns(market_data)
            if not detected_patterns:
                return None
            
            # 가장 강한 패턴 선택
            strongest_pattern = max(detected_patterns, key=lambda p: p["confidence"])
            
            # 신호 생성
            signal = self._create_pattern_signal(market_data, strongest_pattern)
            
            self._update_evaluation_stats(signal)
            return signal
            
        except Exception as e:
            logger.error(f"{self.name} 평가 오류: {e}")
            return None
    
    def _detect_patterns(self, market_data: MarketData) -> List[Dict[str, Any]]:
        """캔들 패턴 감지"""
        patterns = []
        
        try:
            # 최근 3개 캔들 데이터
            if len(market_data.close_prices) >= 3:
                recent_closes = market_data.close_prices[-3:]
                recent_highs = market_data.high_prices[-3:] if len(market_data.high_prices) >= 3 else recent_closes
                recent_lows = market_data.low_prices[-3:] if len(market_data.low_prices) >= 3 else recent_closes
                
                # 각 패턴 검사
                for pattern_type in self.pattern_types:
                    pattern_result = self._check_pattern(pattern_type, recent_closes, recent_highs, recent_lows)
                    if pattern_result:
                        patterns.append(pattern_result)
            
            return patterns
            
        except Exception as e:
            logger.error(f"패턴 감지 오류: {e}")
            return []
    
    def _check_pattern(self, pattern_type: str, closes: List[float], highs: List[float], lows: List[float]) -> Optional[Dict[str, Any]]:
        """특정 패턴 검사"""
        try:
            if pattern_type == "hammer":
                return self._check_hammer_pattern(closes, highs, lows)
            elif pattern_type == "doji":
                return self._check_doji_pattern(closes, highs, lows)
            elif pattern_type == "engulfing":
                return self._check_engulfing_pattern(closes, highs, lows)
            elif pattern_type == "shooting_star":
                return self._check_shooting_star_pattern(closes, highs, lows)
            
            return None
            
        except Exception as e:
            logger.error(f"패턴 검사 오류 ({pattern_type}): {e}")
            return None
    
    def _check_hammer_pattern(self, closes: List[float], highs: List[float], lows: List[float]) -> Optional[Dict[str, Any]]:
        """해머 패턴 검사"""
        if len(closes) < 2:
            return None
        
        # 최근 캔들 (해머 후보)
        current_close = closes[-1]
        current_high = highs[-1]
        current_low = lows[-1]
        
        # 이전 캔들의 종가를 시가로 사용
        current_open = closes[-2] if len(closes) >= 2 else current_close
        
        # 해머 조건 검사
        body_size = abs(current_close - current_open)
        lower_shadow = current_open - current_low if current_open > current_close else current_close - current_low
        upper_shadow = current_high - max(current_open, current_close)
        
        # 해머 패턴 조건
        if (lower_shadow > body_size * 2 and  # 아래 그림자가 몸통의 2배 이상
            upper_shadow < body_size * 0.5 and  # 위 그림자가 몸통의 절반 이하
            body_size > 0):  # 몸통이 존재
            
            confidence = self.pattern_weights.get("hammer", 0.8) * self.pattern_sensitivity
            
            return {
                "type": "hammer",
                "confidence": confidence,
                "signal_type": SignalType.BUY.value,  # 해머는 일반적으로 상승 신호
                "metadata": {
                    "body_size": body_size,
                    "lower_shadow": lower_shadow,
                    "upper_shadow": upper_shadow
                }
            }
        
        return None
    
    def _check_doji_pattern(self, closes: List[float], highs: List[float], lows: List[float]) -> Optional[Dict[str, Any]]:
        """도지 패턴 검사"""
        if len(closes) < 2:
            return None
        
        current_close = closes[-1]
        current_high = highs[-1]
        current_low = lows[-1]
        current_open = closes[-2] if len(closes) >= 2 else current_close
        
        # 도지 조건 검사
        body_size = abs(current_close - current_open)
        total_range = current_high - current_low
        
        # 도지 패턴 조건 (몸통이 전체 범위의 10% 이하)
        if total_range > 0 and body_size / total_range <= 0.1:
            confidence = self.pattern_weights.get("doji", 0.6) * self.pattern_sensitivity
            
            # 도지는 중립적 신호이므로 추가 분석 필요
            signal_type = SignalType.BUY.value  # 기본값, 실제로는 컨텍스트에 따라 결정
            
            return {
                "type": "doji",
                "confidence": confidence,
                "signal_type": signal_type,
                "metadata": {
                    "body_size": body_size,
                    "total_range": total_range,
                    "body_ratio": body_size / total_range if total_range > 0 else 0
                }
            }
        
        return None
    
    def _check_engulfing_pattern(self, closes: List[float], highs: List[float], lows: List[float]) -> Optional[Dict[str, Any]]:
        """포용 패턴 검사"""
        if len(closes) < 3:
            return None
        
        # 3개 캔들 필요 (이전, 현재, 다음 시가용)
        prev_close = closes[-3]
        prev_open = closes[-4] if len(closes) >= 4 else prev_close
        current_close = closes[-2]
        current_open = closes[-3]
        
        # 강세 포용 패턴
        if (prev_close < prev_open and  # 이전 캔들이 음봉
            current_close > current_open and  # 현재 캔들이 양봉
            current_open < prev_close and  # 현재 시가가 이전 종가보다 낮음
            current_close > prev_open):  # 현재 종가가 이전 시가보다 높음
            
            confidence = self.pattern_weights.get("engulfing", 0.9) * self.pattern_sensitivity
            
            return {
                "type": "bullish_engulfing",
                "confidence": confidence,
                "signal_type": SignalType.BUY.value,
                "metadata": {
                    "prev_candle": {"open": prev_open, "close": prev_close},
                    "current_candle": {"open": current_open, "close": current_close}
                }
            }
        
        # 약세 포용 패턴
        elif (prev_close > prev_open and  # 이전 캔들이 양봉
              current_close < current_open and  # 현재 캔들이 음봉
              current_open > prev_close and  # 현재 시가가 이전 종가보다 높음
              current_close < prev_open):  # 현재 종가가 이전 시가보다 낮음
            
            confidence = self.pattern_weights.get("engulfing", 0.9) * self.pattern_sensitivity
            
            return {
                "type": "bearish_engulfing",
                "confidence": confidence,
                "signal_type": SignalType.SELL.value,
                "metadata": {
                    "prev_candle": {"open": prev_open, "close": prev_close},
                    "current_candle": {"open": current_open, "close": current_close}
                }
            }
        
        return None
    
    def _check_shooting_star_pattern(self, closes: List[float], highs: List[float], lows: List[float]) -> Optional[Dict[str, Any]]:
        """유성 패턴 검사"""
        if len(closes) < 2:
            return None
        
        current_close = closes[-1]
        current_high = highs[-1]
        current_low = lows[-1]
        current_open = closes[-2] if len(closes) >= 2 else current_close
        
        # 유성 조건 검사
        body_size = abs(current_close - current_open)
        upper_shadow = current_high - max(current_open, current_close)
        lower_shadow = min(current_open, current_close) - current_low
        
        # 유성 패턴 조건
        if (upper_shadow > body_size * 2 and  # 위 그림자가 몸통의 2배 이상
            lower_shadow < body_size * 0.5 and  # 아래 그림자가 몸통의 절반 이하
            body_size > 0):  # 몸통이 존재
            
            confidence = self.pattern_weights.get("shooting_star", 0.7) * self.pattern_sensitivity
            
            return {
                "type": "shooting_star",
                "confidence": confidence,
                "signal_type": SignalType.SELL.value,  # 유성은 일반적으로 하락 신호
                "metadata": {
                    "body_size": body_size,
                    "upper_shadow": upper_shadow,
                    "lower_shadow": lower_shadow
                }
            }
        
        return None
    
    def _create_pattern_signal(self, market_data: MarketData, pattern: Dict[str, Any]) -> Optional[Signal]:
        """패턴 기반 신호 생성"""
        if pattern["confidence"] < self.confidence_threshold:
            return None
        
        return self._create_signal(
            market_data=market_data,
            signal_type=pattern["signal_type"],
            confidence=pattern["confidence"],
            metadata={
                "pattern": pattern,
                "analysis_type": "advanced_candle_pattern"
            }
        )
