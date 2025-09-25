"""
틱 기반 진입 조건 모듈

이 모듈은 틱 패턴 기반 진입 조건을 구현합니다.
"""

from typing import Optional, Dict, Any, List, Tuple
from core.models import MarketData, Signal, Position, SignalType
from conditions.base_condition import EntryCondition
from utils.logger import get_logger

logger = get_logger(__name__)


class TickBasedCondition(EntryCondition):
    """틱 기반 진입 조건"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("틱 기반 조건", config)
        
        # 틱 패턴 설정
        self.up_ticks = config.get("up_ticks", 3)  # 상승 틱 수
        self.down_ticks = config.get("down_ticks", 2)  # 하락 틱 수
        self.additional_entry_ratio = config.get("additional_entry_ratio", 50)  # 추가 진입 비중 (%)
        
        # 패턴 감지 설정
        self.pattern_type = config.get("pattern_type", "up_then_down")  # up_then_down, down_then_up
        self.tick_size = config.get("tick_size", 0.1)  # 틱 크기
        self.max_pattern_time = config.get("max_pattern_time", 300)  # 최대 패턴 시간 (초)
        
        # 상태 추적
        self.tick_history = []  # 틱 히스토리
        self.pattern_state = "waiting"  # waiting, up_phase, down_phase, completed
        self.pattern_start_time = None
        self.up_tick_count = 0
        self.down_tick_count = 0
        self.last_price = None
        
        logger.info(f"틱 기반 조건 초기화: 상승={self.up_ticks}틱, 하락={self.down_ticks}틱, 패턴={self.pattern_type}")
    
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """틱 기반 조건 평가"""
        try:
            # 기본 검증
            if not self.is_active():
                return None
            
            if not self._validate_market_data(market_data):
                return None
            
            # 틱 데이터 업데이트
            self._update_tick_data(market_data)
            
            # 패턴 상태 업데이트
            self._update_pattern_state(market_data)
            
            # 신호 평가
            signal = self._evaluate_tick_pattern(market_data, position)
            
            # 평가 통계 업데이트
            self._update_evaluation_stats(signal)
            
            if signal:
                logger.info(f"{self.name}: 신호 생성 - {signal.type.value} at {signal.price} (패턴: {self.pattern_state})")
            
            return signal
            
        except Exception as e:
            logger.error(f"{self.name} 평가 오류: {e}")
            return None
    
    def _update_tick_data(self, market_data: MarketData) -> None:
        """틱 데이터 업데이트"""
        try:
            current_price = market_data.current_price
            current_time = market_data.timestamp
            
            # 첫 번째 가격이면 초기화
            if self.last_price is None:
                self.last_price = current_price
                return
            
            # 가격 변화 계산
            price_change = current_price - self.last_price
            
            # 틱 변화가 있을 때만 기록
            if abs(price_change) >= self.tick_size:
                tick_direction = "up" if price_change > 0 else "down"
                tick_count = int(abs(price_change) / self.tick_size)
                
                # 틱 히스토리에 추가
                tick_data = {
                    "price": current_price,
                    "direction": tick_direction,
                    "count": tick_count,
                    "timestamp": current_time,
                    "price_change": price_change
                }
                
                self.tick_history.append(tick_data)
                
                # 히스토리 크기 제한 (최근 100개)
                if len(self.tick_history) > 100:
                    self.tick_history.pop(0)
                
                self.last_price = current_price
                
                logger.debug(f"{self.name}: 틱 업데이트 - 방향: {tick_direction}, 수: {tick_count}, 가격: {current_price}")
            
        except Exception as e:
            logger.error(f"틱 데이터 업데이트 오류: {e}")
    
    def _update_pattern_state(self, market_data: MarketData) -> None:
        """패턴 상태 업데이트"""
        try:
            current_time = market_data.timestamp
            
            # 패턴 타임아웃 체크
            if (self.pattern_start_time and 
                current_time - self.pattern_start_time > self.max_pattern_time):
                self._reset_pattern_state()
                return
            
            # 최근 틱 데이터가 없으면 리턴
            if not self.tick_history:
                return
            
            recent_tick = self.tick_history[-1]
            
            # 패턴 타입에 따른 상태 업데이트
            if self.pattern_type == "up_then_down":
                self._update_up_then_down_pattern(recent_tick, current_time)
            elif self.pattern_type == "down_then_up":
                self._update_down_then_up_pattern(recent_tick, current_time)
            
        except Exception as e:
            logger.error(f"패턴 상태 업데이트 오류: {e}")
    
    def _update_up_then_down_pattern(self, recent_tick: Dict[str, Any], current_time: float) -> None:
        """상승→하락 패턴 상태 업데이트"""
        if self.pattern_state == "waiting":
            # 상승 틱 시작
            if recent_tick["direction"] == "up":
                self.pattern_state = "up_phase"
                self.pattern_start_time = current_time
                self.up_tick_count = recent_tick["count"]
                self.down_tick_count = 0
                logger.debug(f"{self.name}: 상승 단계 시작 - {self.up_tick_count}틱")
        
        elif self.pattern_state == "up_phase":
            if recent_tick["direction"] == "up":
                # 상승 틱 계속
                self.up_tick_count += recent_tick["count"]
            elif recent_tick["direction"] == "down":
                # 하락 틱 시작 - 충분한 상승 틱이 있었는지 확인
                if self.up_tick_count >= self.up_ticks:
                    self.pattern_state = "down_phase"
                    self.down_tick_count = recent_tick["count"]
                    logger.debug(f"{self.name}: 하락 단계 시작 - 상승 {self.up_tick_count}틱 완료")
                else:
                    # 충분하지 않으면 리셋
                    self._reset_pattern_state()
        
        elif self.pattern_state == "down_phase":
            if recent_tick["direction"] == "down":
                # 하락 틱 계속
                self.down_tick_count += recent_tick["count"]
                
                # 패턴 완성 체크
                if self.down_tick_count >= self.down_ticks:
                    self.pattern_state = "completed"
                    logger.info(f"{self.name}: 패턴 완성 - 상승 {self.up_tick_count}틱 → 하락 {self.down_tick_count}틱")
            
            elif recent_tick["direction"] == "up":
                # 상승 틱으로 전환 - 패턴 실패
                self._reset_pattern_state()
    
    def _update_down_then_up_pattern(self, recent_tick: Dict[str, Any], current_time: float) -> None:
        """하락→상승 패턴 상태 업데이트"""
        if self.pattern_state == "waiting":
            # 하락 틱 시작
            if recent_tick["direction"] == "down":
                self.pattern_state = "down_phase"
                self.pattern_start_time = current_time
                self.down_tick_count = recent_tick["count"]
                self.up_tick_count = 0
                logger.debug(f"{self.name}: 하락 단계 시작 - {self.down_tick_count}틱")
        
        elif self.pattern_state == "down_phase":
            if recent_tick["direction"] == "down":
                # 하락 틱 계속
                self.down_tick_count += recent_tick["count"]
            elif recent_tick["direction"] == "up":
                # 상승 틱 시작 - 충분한 하락 틱이 있었는지 확인
                if self.down_tick_count >= self.down_ticks:
                    self.pattern_state = "up_phase"
                    self.up_tick_count = recent_tick["count"]
                    logger.debug(f"{self.name}: 상승 단계 시작 - 하락 {self.down_tick_count}틱 완료")
                else:
                    # 충분하지 않으면 리셋
                    self._reset_pattern_state()
        
        elif self.pattern_state == "up_phase":
            if recent_tick["direction"] == "up":
                # 상승 틱 계속
                self.up_tick_count += recent_tick["count"]
                
                # 패턴 완성 체크
                if self.up_tick_count >= self.up_ticks:
                    self.pattern_state = "completed"
                    logger.info(f"{self.name}: 패턴 완성 - 하락 {self.down_tick_count}틱 → 상승 {self.up_tick_count}틱")
            
            elif recent_tick["direction"] == "down":
                # 하락 틱으로 전환 - 패턴 실패
                self._reset_pattern_state()
    
    def _reset_pattern_state(self) -> None:
        """패턴 상태 리셋"""
        self.pattern_state = "waiting"
        self.pattern_start_time = None
        self.up_tick_count = 0
        self.down_tick_count = 0
        logger.debug(f"{self.name}: 패턴 상태 리셋")
    
    def _evaluate_tick_pattern(self, market_data: MarketData, position: Optional[Position]) -> Optional[Signal]:
        """틱 패턴 신호 평가"""
        # 패턴이 완성되었을 때만 신호 생성
        if self.pattern_state != "completed":
            return None
        
        # 기존 포지션이 있는 경우에만 추가 진입 (PRD 요구사항)
        if not position:
            logger.debug(f"{self.name}: 기존 포지션 없음 - 추가 진입 불가")
            self._reset_pattern_state()  # 패턴 리셋
            return None
        
        # 신호 타입 결정
        if self.pattern_type == "up_then_down":
            # 상승 후 하락 → 추가 매수 (평단가 낮추기)
            signal_type = SignalType.BUY
        else:  # down_then_up
            # 하락 후 상승 → 추가 매도 (평단가 높이기)
            signal_type = SignalType.SELL
        
        # 신뢰도 계산
        confidence = self._calculate_pattern_confidence()
        
        if confidence >= self.confidence_threshold:
            metadata = {
                "pattern_type": self.pattern_type,
                "up_tick_count": self.up_tick_count,
                "down_tick_count": self.down_tick_count,
                "additional_entry": True,
                "entry_ratio": self.additional_entry_ratio,
                "existing_position": {
                    "symbol": position.symbol if position else None,
                    "side": position.side if position else None,
                    "quantity": position.quantity if position else None
                }
            }
            
            signal = self._create_signal(
                market_data=market_data,
                signal_type=signal_type.value,
                confidence=confidence,
                metadata=metadata
            )
            
            # 신호 생성 후 패턴 리셋
            self._reset_pattern_state()
            
            return signal
        
        # 신뢰도가 낮으면 패턴 리셋
        self._reset_pattern_state()
        return None
    
    def _calculate_pattern_confidence(self) -> float:
        """패턴 신뢰도 계산"""
        try:
            # 기본 신뢰도 (패턴 완성도 기반)
            up_completion = min(self.up_tick_count / self.up_ticks, 2.0)  # 최대 200%
            down_completion = min(self.down_tick_count / self.down_ticks, 2.0)  # 최대 200%
            
            base_confidence = (up_completion + down_completion) / 4.0  # 평균 후 정규화
            
            # 패턴 시간 보정 (빠를수록 신뢰도 높음)
            if self.pattern_start_time:
                pattern_duration = self.tick_history[-1]["timestamp"] - self.pattern_start_time
                time_factor = max(0.5, 1.0 - (pattern_duration / self.max_pattern_time))
            else:
                time_factor = 1.0
            
            # 틱 수 보정 (많을수록 신뢰도 높음)
            tick_factor = min((self.up_tick_count + self.down_tick_count) / 10.0, 1.2)
            
            # 최종 신뢰도
            confidence = base_confidence * time_factor * tick_factor
            confidence = max(0.3, min(1.0, confidence))  # 30% ~ 100%
            
            logger.debug(f"{self.name}: 패턴 신뢰도 - 기본: {base_confidence:.2f}, 시간: {time_factor:.2f}, 틱: {tick_factor:.2f}, 최종: {confidence:.2f}")
            return confidence
            
        except Exception as e:
            logger.error(f"패턴 신뢰도 계산 오류: {e}")
            return 0.0
    
    def get_pattern_status(self, market_data: MarketData) -> Dict[str, Any]:
        """패턴 상태 정보 반환 (GUI 표시용)"""
        # 현재 패턴 진행률 계산
        up_progress = (self.up_tick_count / self.up_ticks) * 100 if self.up_ticks > 0 else 0
        down_progress = (self.down_tick_count / self.down_ticks) * 100 if self.down_ticks > 0 else 0
        
        # 전체 진행률
        if self.pattern_state == "waiting":
            total_progress = 0
        elif self.pattern_state == "up_phase":
            total_progress = up_progress * 0.5  # 첫 번째 단계는 전체의 50%
        elif self.pattern_state == "down_phase":
            total_progress = 50 + (down_progress * 0.5)  # 두 번째 단계는 나머지 50%
        elif self.pattern_state == "completed":
            total_progress = 100
        else:
            total_progress = 0
        
        # 패턴 시간 정보
        pattern_duration = 0
        if self.pattern_start_time and self.tick_history:
            pattern_duration = self.tick_history[-1]["timestamp"] - self.pattern_start_time
        
        return {
            "pattern_state": self.pattern_state,
            "pattern_type": self.pattern_type,
            "up_tick_count": self.up_tick_count,
            "down_tick_count": self.down_tick_count,
            "up_tick_target": self.up_ticks,
            "down_tick_target": self.down_ticks,
            "up_progress": min(up_progress, 100),
            "down_progress": min(down_progress, 100),
            "total_progress": min(total_progress, 100),
            "pattern_duration": pattern_duration,
            "max_pattern_time": self.max_pattern_time,
            "recent_ticks": self.tick_history[-5:] if len(self.tick_history) >= 5 else self.tick_history
        }
    
    def force_reset_pattern(self) -> None:
        """패턴 강제 리셋 (GUI 버튼용)"""
        self._reset_pattern_state()
        self.tick_history.clear()
        self.last_price = None
        logger.info(f"{self.name}: 패턴 강제 리셋")
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """설정 업데이트"""
        super().update_config(new_config)
        
        # 틱 기반 특화 설정 업데이트
        self.up_ticks = self.config.get("up_ticks", self.up_ticks)
        self.down_ticks = self.config.get("down_ticks", self.down_ticks)
        self.additional_entry_ratio = self.config.get("additional_entry_ratio", self.additional_entry_ratio)
        self.pattern_type = self.config.get("pattern_type", self.pattern_type)
        self.tick_size = self.config.get("tick_size", self.tick_size)
        
        # 설정 변경 시 패턴 리셋
        self._reset_pattern_state()
        
        logger.info(f"{self.name} 설정 업데이트: 상승={self.up_ticks}, 하락={self.down_ticks}, 패턴={self.pattern_type}")
    
    def get_status(self) -> Dict[str, Any]:
        """상태 정보 반환"""
        status = super().get_status()
        status.update({
            "up_ticks": self.up_ticks,
            "down_ticks": self.down_ticks,
            "pattern_type": self.pattern_type,
            "pattern_state": self.pattern_state,
            "additional_entry_ratio": self.additional_entry_ratio,
            "tick_history_size": len(self.tick_history)
        })
        return status
    
    def __str__(self) -> str:
        """문자열 표현"""
        return f"틱 기반 조건 (패턴: {self.pattern_type}, 상승: {self.up_ticks}틱, 하락: {self.down_ticks}틱)"


class AdvancedTickAnalysisCondition(EntryCondition):
    """고급 틱 분석 조건"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("고급 틱 분석 조건", config)
        
        # 고급 분석 설정
        self.velocity_analysis = config.get("velocity_analysis", True)  # 틱 속도 분석
        self.volume_weighted = config.get("volume_weighted", False)  # 볼륨 가중 분석
        self.momentum_threshold = config.get("momentum_threshold", 0.7)  # 모멘텀 임계값
        
        # 분석 윈도우
        self.analysis_window = config.get("analysis_window", 20)  # 분석 윈도우 크기
        
        logger.info(f"고급 틱 분석 조건 초기화: 속도분석={self.velocity_analysis}, 볼륨가중={self.volume_weighted}")
    
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """고급 틱 분석 조건 평가"""
        try:
            if not self.is_active() or not self._validate_market_data(market_data):
                return None
            
            # 틱 데이터 수집
            tick_data = self._collect_tick_data(market_data)
            if len(tick_data) < self.analysis_window:
                return None
            
            # 고급 분석 수행
            analysis_result = self._perform_advanced_analysis(tick_data, market_data)
            if not analysis_result:
                return None
            
            # 신호 생성
            signal = self._create_advanced_signal(market_data, analysis_result)
            
            self._update_evaluation_stats(signal)
            return signal
            
        except Exception as e:
            logger.error(f"{self.name} 평가 오류: {e}")
            return None
    
    def _collect_tick_data(self, market_data: MarketData) -> List[Dict[str, Any]]:
        """틱 데이터 수집 (시뮬레이션)"""
        # 실제 구현에서는 실시간 틱 데이터를 수집해야 함
        # 여기서는 가격 변화를 기반으로 시뮬레이션
        tick_data = []
        
        if len(market_data.close_prices) >= self.analysis_window:
            prices = market_data.close_prices[-self.analysis_window:]
            
            for i in range(1, len(prices)):
                price_change = prices[i] - prices[i-1]
                tick_data.append({
                    "price": prices[i],
                    "change": price_change,
                    "timestamp": market_data.timestamp - (len(prices) - i) * 60,  # 1분 간격 가정
                    "volume": 1000  # 시뮬레이션 볼륨
                })
        
        return tick_data
    
    def _perform_advanced_analysis(self, tick_data: List[Dict[str, Any]], market_data: MarketData) -> Optional[Dict[str, Any]]:
        """고급 틱 분석 수행"""
        try:
            analysis = {}
            
            # 틱 속도 분석
            if self.velocity_analysis:
                velocity_result = self._analyze_tick_velocity(tick_data)
                analysis["velocity"] = velocity_result
            
            # 볼륨 가중 분석
            if self.volume_weighted:
                volume_result = self._analyze_volume_weighted_ticks(tick_data)
                analysis["volume_weighted"] = volume_result
            
            # 모멘텀 분석
            momentum_result = self._analyze_tick_momentum(tick_data)
            analysis["momentum"] = momentum_result
            
            # 종합 점수 계산
            overall_score = self._calculate_overall_score(analysis)
            analysis["overall_score"] = overall_score
            
            # 임계값 체크
            if overall_score >= self.momentum_threshold:
                return analysis
            
            return None
            
        except Exception as e:
            logger.error(f"고급 틱 분석 오류: {e}")
            return None
    
    def _analyze_tick_velocity(self, tick_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """틱 속도 분석"""
        if len(tick_data) < 2:
            return {"velocity": 0.0, "acceleration": 0.0}
        
        # 가격 변화 속도 계산
        velocities = []
        for i in range(1, len(tick_data)):
            time_diff = tick_data[i]["timestamp"] - tick_data[i-1]["timestamp"]
            if time_diff > 0:
                velocity = abs(tick_data[i]["change"]) / time_diff
                velocities.append(velocity)
        
        if not velocities:
            return {"velocity": 0.0, "acceleration": 0.0}
        
        avg_velocity = sum(velocities) / len(velocities)
        
        # 가속도 계산 (속도의 변화율)
        acceleration = 0.0
        if len(velocities) >= 2:
            recent_velocity = sum(velocities[-3:]) / min(3, len(velocities))
            early_velocity = sum(velocities[:3]) / min(3, len(velocities))
            acceleration = recent_velocity - early_velocity
        
        return {
            "velocity": avg_velocity,
            "acceleration": acceleration,
            "max_velocity": max(velocities),
            "velocity_trend": "increasing" if acceleration > 0 else "decreasing"
        }
    
    def _analyze_volume_weighted_ticks(self, tick_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """볼륨 가중 틱 분석"""
        total_volume = sum(tick["volume"] for tick in tick_data)
        if total_volume == 0:
            return {"weighted_change": 0.0, "volume_momentum": 0.0}
        
        # 볼륨 가중 가격 변화
        weighted_change = sum(tick["change"] * tick["volume"] for tick in tick_data) / total_volume
        
        # 볼륨 모멘텀 (최근 볼륨 vs 평균 볼륨)
        avg_volume = total_volume / len(tick_data)
        recent_volume = sum(tick["volume"] for tick in tick_data[-5:]) / min(5, len(tick_data))
        volume_momentum = (recent_volume - avg_volume) / avg_volume if avg_volume > 0 else 0
        
        return {
            "weighted_change": weighted_change,
            "volume_momentum": volume_momentum,
            "total_volume": total_volume,
            "avg_volume": avg_volume
        }
    
    def _analyze_tick_momentum(self, tick_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """틱 모멘텀 분석"""
        if len(tick_data) < 5:
            return {"momentum": 0.0, "direction": "neutral"}
        
        # 가격 변화 방향성 분석
        positive_changes = sum(1 for tick in tick_data if tick["change"] > 0)
        negative_changes = sum(1 for tick in tick_data if tick["change"] < 0)
        
        # 모멘텀 계산
        total_changes = positive_changes + negative_changes
        if total_changes == 0:
            momentum = 0.0
            direction = "neutral"
        else:
            momentum = abs(positive_changes - negative_changes) / total_changes
            direction = "bullish" if positive_changes > negative_changes else "bearish"
        
        # 최근 모멘텀 (최근 5개 틱)
        recent_ticks = tick_data[-5:]
        recent_positive = sum(1 for tick in recent_ticks if tick["change"] > 0)
        recent_negative = sum(1 for tick in recent_ticks if tick["change"] < 0)
        recent_total = recent_positive + recent_negative
        
        recent_momentum = 0.0
        if recent_total > 0:
            recent_momentum = abs(recent_positive - recent_negative) / recent_total
        
        return {
            "momentum": momentum,
            "direction": direction,
            "recent_momentum": recent_momentum,
            "positive_ratio": positive_changes / len(tick_data),
            "negative_ratio": negative_changes / len(tick_data)
        }
    
    def _calculate_overall_score(self, analysis: Dict[str, Any]) -> float:
        """종합 점수 계산"""
        try:
            score = 0.0
            weight_sum = 0.0
            
            # 속도 분석 점수
            if "velocity" in analysis:
                velocity_score = min(analysis["velocity"]["velocity"] / 10.0, 1.0)  # 정규화
                acceleration_bonus = max(0, analysis["velocity"]["acceleration"] / 5.0)
                velocity_total = min(velocity_score + acceleration_bonus, 1.0)
                
                score += velocity_total * 0.4  # 40% 가중치
                weight_sum += 0.4
            
            # 볼륨 가중 점수
            if "volume_weighted" in analysis:
                volume_score = min(abs(analysis["volume_weighted"]["weighted_change"]) / 5.0, 1.0)
                momentum_bonus = max(0, analysis["volume_weighted"]["volume_momentum"])
                volume_total = min(volume_score + momentum_bonus, 1.0)
                
                score += volume_total * 0.3  # 30% 가중치
                weight_sum += 0.3
            
            # 모멘텀 점수
            if "momentum" in analysis:
                momentum_score = analysis["momentum"]["momentum"]
                recent_bonus = analysis["momentum"]["recent_momentum"] * 0.2
                momentum_total = min(momentum_score + recent_bonus, 1.0)
                
                score += momentum_total * 0.3  # 30% 가중치
                weight_sum += 0.3
            
            # 가중 평균 계산
            if weight_sum > 0:
                final_score = score / weight_sum
            else:
                final_score = 0.0
            
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            logger.error(f"종합 점수 계산 오류: {e}")
            return 0.0
    
    def _create_advanced_signal(self, market_data: MarketData, analysis: Dict[str, Any]) -> Optional[Signal]:
        """고급 분석 기반 신호 생성"""
        overall_score = analysis["overall_score"]
        
        # 신호 방향 결정
        signal_type = SignalType.BUY  # 기본값
        
        if "momentum" in analysis:
            direction = analysis["momentum"]["direction"]
            if direction == "bearish":
                signal_type = SignalType.SELL
        
        return self._create_signal(
            market_data=market_data,
            signal_type=signal_type.value,
            confidence=overall_score,
            metadata={
                "analysis": analysis,
                "analysis_type": "advanced_tick_analysis"
            }
        )
