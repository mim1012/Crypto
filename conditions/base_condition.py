"""
조건 기본 클래스 모듈

이 모듈은 모든 진입/청산 조건의 기본 클래스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from core.models import MarketData, Signal, Position
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseCondition(ABC):
    """조건 기본 클래스"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.is_enabled = config.get("enabled", False)
        
        # 조건 상태
        self.last_evaluation_time = 0
        self.last_signal = None
        self.evaluation_count = 0
        
        logger.debug(f"조건 초기화: {self.name}")
    
    @abstractmethod
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """
        조건 평가 (추상 메서드)
        
        Args:
            market_data: 시장 데이터
            position: 포지션 (청산 조건의 경우)
            
        Returns:
            Signal: 조건이 만족되면 신호 반환, 아니면 None
        """
        pass
    
    def is_active(self) -> bool:
        """조건이 활성화되어 있는지 확인"""
        return self.is_enabled
    
    def enable(self) -> None:
        """조건 활성화"""
        self.is_enabled = True
        logger.info(f"조건 활성화: {self.name}")
    
    def disable(self) -> None:
        """조건 비활성화"""
        self.is_enabled = False
        logger.info(f"조건 비활성화: {self.name}")
    
    def get_name(self) -> str:
        """조건 이름 반환"""
        return self.name
    
    def get_config(self) -> Dict[str, Any]:
        """조건 설정 반환"""
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """조건 설정 업데이트"""
        self.config.update(new_config)
        self.is_enabled = self.config.get("enabled", self.is_enabled)
        logger.info(f"조건 설정 업데이트: {self.name}")
    
    def get_status(self) -> Dict[str, Any]:
        """조건 상태 반환"""
        return {
            "name": self.name,
            "enabled": self.is_enabled,
            "evaluation_count": self.evaluation_count,
            "last_evaluation_time": self.last_evaluation_time,
            "last_signal": self.last_signal.type.value if self.last_signal else None
        }
    
    def _update_evaluation_stats(self, signal: Optional[Signal]) -> None:
        """평가 통계 업데이트"""
        import time
        self.evaluation_count += 1
        self.last_evaluation_time = int(time.time())
        self.last_signal = signal
    
    def _validate_market_data(self, market_data: MarketData) -> bool:
        """시장 데이터 유효성 검증"""
        if not market_data:
            logger.warning(f"{self.name}: 시장 데이터가 없습니다")
            return False
        
        if not market_data.close_prices:
            logger.warning(f"{self.name}: 종가 데이터가 없습니다")
            return False
        
        if market_data.current_price <= 0:
            logger.warning(f"{self.name}: 현재가가 올바르지 않습니다")
            return False
        
        return True
    
    def __str__(self) -> str:
        """문자열 표현"""
        status = "활성화" if self.is_enabled else "비활성화"
        return f"{self.name} ({status})"
    
    def __repr__(self) -> str:
        """객체 표현"""
        return f"{self.__class__.__name__}(name='{self.name}', enabled={self.is_enabled})"


class EntryCondition(BaseCondition):
    """진입 조건 기본 클래스"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
        # 진입 조건 특화 설정
        self.signal_type = config.get("signal_type", "BUY")
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        
    @abstractmethod
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """진입 조건 평가"""
        pass
    
    def _create_signal(self, 
                      market_data: MarketData, 
                      signal_type: str, 
                      confidence: float,
                      metadata: Optional[Dict[str, Any]] = None) -> Signal:
        """신호 생성 헬퍼 메서드"""
        from core.models import SignalType
        
        return Signal(
            type=SignalType(signal_type),
            symbol=market_data.symbol,
            price=market_data.current_price,
            confidence=confidence,
            source=self.name,
            metadata=metadata or {}
        )


class ExitCondition(BaseCondition):
    """청산 조건 기본 클래스"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        
        # 청산 조건 특화 설정
        self.exit_percentage = config.get("exit_percentage", 100.0)  # 청산 비율
        self.partial_exit_enabled = config.get("partial_exit_enabled", False)
    
    @abstractmethod
    def evaluate(self, market_data: MarketData, position: Position) -> Optional[Signal]:
        """청산 조건 평가"""
        pass
    
    def _create_exit_signal(self, 
                           market_data: MarketData, 
                           position: Position,
                           confidence: float,
                           metadata: Optional[Dict[str, Any]] = None) -> Signal:
        """청산 신호 생성 헬퍼 메서드"""
        from core.models import SignalType
        
        # 포지션과 반대 방향으로 신호 생성
        signal_type = SignalType.SELL if position.is_long() else SignalType.BUY
        
        return Signal(
            type=signal_type,
            symbol=market_data.symbol,
            price=market_data.current_price,
            confidence=confidence,
            source=self.name,
            metadata=metadata or {}
        )
    
    def _validate_position(self, position: Position) -> bool:
        """포지션 유효성 검증"""
        if not position:
            logger.warning(f"{self.name}: 포지션이 없습니다")
            return False
        
        if position.size <= 0:
            logger.warning(f"{self.name}: 포지션 크기가 올바르지 않습니다")
            return False
        
        return True


class ConditionManager:
    """조건 관리자 클래스"""
    
    def __init__(self):
        self.entry_conditions = []
        self.exit_conditions = []
        self.combination_mode = "OR"  # "AND" or "OR"
        
        logger.info("조건 관리자 초기화")
    
    def add_entry_condition(self, condition: EntryCondition) -> None:
        """진입 조건 추가"""
        self.entry_conditions.append(condition)
        logger.info(f"진입 조건 추가: {condition.get_name()}")
    
    def add_exit_condition(self, condition: ExitCondition) -> None:
        """청산 조건 추가"""
        self.exit_conditions.append(condition)
        logger.info(f"청산 조건 추가: {condition.get_name()}")
    
    def remove_entry_condition(self, condition_name: str) -> bool:
        """진입 조건 제거"""
        for i, condition in enumerate(self.entry_conditions):
            if condition.get_name() == condition_name:
                del self.entry_conditions[i]
                logger.info(f"진입 조건 제거: {condition_name}")
                return True
        return False
    
    def remove_exit_condition(self, condition_name: str) -> bool:
        """청산 조건 제거"""
        for i, condition in enumerate(self.exit_conditions):
            if condition.get_name() == condition_name:
                del self.exit_conditions[i]
                logger.info(f"청산 조건 제거: {condition_name}")
                return True
        return False
    
    def set_combination_mode(self, mode: str) -> None:
        """조합 모드 설정"""
        if mode in ["AND", "OR"]:
            self.combination_mode = mode
            logger.info(f"조합 모드 설정: {mode}")
        else:
            logger.warning(f"올바르지 않은 조합 모드: {mode}")
    
    def evaluate_entry_conditions(self, market_data: MarketData) -> Optional[Signal]:
        """진입 조건들 평가"""
        if not self.entry_conditions:
            return None
        
        active_conditions = [c for c in self.entry_conditions if c.is_active()]
        if not active_conditions:
            return None
        
        signals = []
        for condition in active_conditions:
            try:
                signal = condition.evaluate(market_data)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"진입 조건 평가 오류 ({condition.get_name()}): {e}")
        
        return self._combine_entry_signals(signals, market_data)
    
    def evaluate_exit_conditions(self, market_data: MarketData, position: Position) -> Optional[Signal]:
        """청산 조건들 평가"""
        if not self.exit_conditions:
            return None
        
        active_conditions = [c for c in self.exit_conditions if c.is_active()]
        if not active_conditions:
            return None
        
        for condition in active_conditions:
            try:
                signal = condition.evaluate(market_data, position)
                if signal:
                    return signal  # 청산 조건은 첫 번째 신호 즉시 반환
            except Exception as e:
                logger.error(f"청산 조건 평가 오류 ({condition.get_name()}): {e}")
        
        return None
    
    def _combine_entry_signals(self, signals: list, market_data: MarketData) -> Optional[Signal]:
        """진입 신호들 조합"""
        if not signals:
            return None
        
        if self.combination_mode == "AND":
            # 모든 조건이 만족되어야 함
            if len(signals) == len([c for c in self.entry_conditions if c.is_active()]):
                # 평균 신뢰도로 통합 신호 생성
                avg_confidence = sum(s.confidence for s in signals) / len(signals)
                return self._create_combined_signal(signals[0], avg_confidence, "AND_COMBINATION")
        else:  # OR
            # 하나 이상의 조건이 만족되면 됨
            # 가장 높은 신뢰도의 신호 반환
            best_signal = max(signals, key=lambda s: s.confidence)
            return best_signal
        
        return None
    
    def _create_combined_signal(self, base_signal: Signal, confidence: float, source: str) -> Signal:
        """조합된 신호 생성"""
        from core.models import Signal
        
        return Signal(
            type=base_signal.type,
            symbol=base_signal.symbol,
            price=base_signal.price,
            confidence=confidence,
            source=source,
            metadata={"combined": True, "original_source": base_signal.source}
        )
    
    def get_active_entry_conditions(self) -> list:
        """활성화된 진입 조건들 반환"""
        return [c for c in self.entry_conditions if c.is_active()]
    
    def get_active_exit_conditions(self) -> list:
        """활성화된 청산 조건들 반환"""
        return [c for c in self.exit_conditions if c.is_active()]
    
    def get_condition_status(self) -> Dict[str, Any]:
        """모든 조건 상태 반환"""
        return {
            "combination_mode": self.combination_mode,
            "entry_conditions": [c.get_status() for c in self.entry_conditions],
            "exit_conditions": [c.get_status() for c in self.exit_conditions],
            "active_entry_count": len(self.get_active_entry_conditions()),
            "active_exit_count": len(self.get_active_exit_conditions())
        }
    
    def enable_all_conditions(self) -> None:
        """모든 조건 활성화"""
        for condition in self.entry_conditions + self.exit_conditions:
            condition.enable()
        logger.info("모든 조건 활성화")
    
    def disable_all_conditions(self) -> None:
        """모든 조건 비활성화"""
        for condition in self.entry_conditions + self.exit_conditions:
            condition.disable()
        logger.info("모든 조건 비활성화")
