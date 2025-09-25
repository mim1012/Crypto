"""
호가 감시 진입 조건 모듈

이 모듈은 호가창 변화 기반 진입 조건을 구현합니다.
"""

from typing import Optional, Dict, Any, List
from core.models import MarketData, Signal, Position, SignalType
from conditions.base_condition import EntryCondition
from utils.logger import get_logger

logger = get_logger(__name__)


class OrderbookWatchCondition(EntryCondition):
    """호가 감시 진입 조건"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("호가 감시 조건", config)
        
        # 호가 감시 설정
        self.tick_threshold = config.get("tick_threshold", 5)  # 틱 임계값
        self.direction = config.get("direction", "both")  # up, down, both
        self.base_price_source = config.get("base_price_source", "open")  # open, close
        
        # 즉시 진입 설정 (0틱)
        self.immediate_entry = config.get("immediate_entry", False)
        
        # 틱 크기 설정 (거래소별로 다름)
        self.tick_size = config.get("tick_size", 0.1)  # BTCUSDT 기본 틱 크기
        
        # 상태 추적
        self.base_price = None
        self.tick_count = 0
        self.last_price = None
        
        logger.info(f"호가 감시 조건 초기화: 임계값={self.tick_threshold}틱, 방향={self.direction}")
    
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """호가 감시 조건 평가"""
        try:
            # 기본 검증
            if not self.is_active():
                return None
            
            if not self._validate_market_data(market_data):
                return None
            
            # 기준가 설정
            if not self._update_base_price(market_data):
                return None
            
            # 틱 변화 계산
            tick_change = self._calculate_tick_change(market_data.current_price)
            
            # 신호 평가
            signal = self._evaluate_tick_signal(market_data, tick_change)
            
            # 평가 통계 업데이트
            self._update_evaluation_stats(signal)
            
            if signal:
                logger.info(f"{self.name}: 신호 생성 - {signal.type.value} at {signal.price} (틱변화: {tick_change})")
            
            return signal
            
        except Exception as e:
            logger.error(f"{self.name} 평가 오류: {e}")
            return None
    
    def _update_base_price(self, market_data: MarketData) -> bool:
        """기준가 업데이트"""
        try:
            # 새 봉 시작 시 기준가 재설정
            if self.base_price_source == "open":
                # 시가를 기준가로 사용 (새 봉 시작 시)
                if len(market_data.close_prices) > 0:
                    new_base_price = market_data.close_prices[-1]  # 이전 봉의 종가 = 현재 봉의 시가
                else:
                    new_base_price = market_data.current_price
            else:  # close
                # 종가를 기준가로 사용
                if len(market_data.close_prices) > 0:
                    new_base_price = market_data.close_prices[-1]
                else:
                    new_base_price = market_data.current_price
            
            # 기준가 변경 시 틱 카운트 리셋
            if self.base_price != new_base_price:
                self.base_price = new_base_price
                self.tick_count = 0
                logger.debug(f"{self.name}: 기준가 업데이트 - {self.base_price:.4f}")
            
            return True
            
        except Exception as e:
            logger.error(f"기준가 업데이트 오류: {e}")
            return False
    
    def _calculate_tick_change(self, current_price: float) -> int:
        """틱 변화 계산"""
        try:
            if self.base_price is None:
                return 0
            
            price_diff = current_price - self.base_price
            tick_change = int(price_diff / self.tick_size)
            
            # 틱 카운트 업데이트
            self.tick_count = tick_change
            self.last_price = current_price
            
            logger.debug(f"{self.name}: 틱 변화 - 기준가: {self.base_price:.4f}, 현재가: {current_price:.4f}, 틱: {tick_change}")
            return tick_change
            
        except Exception as e:
            logger.error(f"틱 변화 계산 오류: {e}")
            return 0
    
    def _evaluate_tick_signal(self, market_data: MarketData, tick_change: int) -> Optional[Signal]:
        """틱 신호 평가"""
        # 즉시 진입 모드 (0틱)
        if self.immediate_entry:
            return self._create_immediate_signal(market_data)
        
        # 상승 틱 신호
        if self.direction in ["up", "both"] and tick_change >= self.tick_threshold:
            confidence = self._calculate_tick_confidence(tick_change, "up")
            if confidence >= self.confidence_threshold:
                metadata = {
                    "tick_change": tick_change,
                    "base_price": self.base_price,
                    "direction": "up",
                    "threshold": self.tick_threshold
                }
                
                return self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.BUY.value,
                    confidence=confidence,
                    metadata=metadata
                )
        
        # 하락 틱 신호
        elif self.direction in ["down", "both"] and tick_change <= -self.tick_threshold:
            confidence = self._calculate_tick_confidence(abs(tick_change), "down")
            if confidence >= self.confidence_threshold:
                metadata = {
                    "tick_change": tick_change,
                    "base_price": self.base_price,
                    "direction": "down",
                    "threshold": self.tick_threshold
                }
                
                return self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.SELL.value,
                    confidence=confidence,
                    metadata=metadata
                )
        
        return None
    
    def _create_immediate_signal(self, market_data: MarketData) -> Optional[Signal]:
        """즉시 진입 신호 생성"""
        # 0틱 설정 시 즉시 진입
        if self.direction == "up":
            signal_type = SignalType.BUY
        elif self.direction == "down":
            signal_type = SignalType.SELL
        else:  # both - 가격 변화 방향에 따라 결정
            if self.last_price and market_data.current_price > self.last_price:
                signal_type = SignalType.BUY
            elif self.last_price and market_data.current_price < self.last_price:
                signal_type = SignalType.SELL
            else:
                return None
        
        confidence = 0.8  # 즉시 진입은 높은 신뢰도
        metadata = {
            "immediate_entry": True,
            "base_price": self.base_price,
            "direction": self.direction
        }
        
        return self._create_signal(
            market_data=market_data,
            signal_type=signal_type.value,
            confidence=confidence,
            metadata=metadata
        )
    
    def _calculate_tick_confidence(self, tick_count: int, direction: str) -> float:
        """틱 신뢰도 계산"""
        try:
            # 틱 수가 많을수록 신뢰도 높음
            base_confidence = min(tick_count / (self.tick_threshold * 2), 0.9)
            
            # 최소 신뢰도 보장
            confidence = max(0.4, base_confidence)
            
            logger.debug(f"{self.name}: 틱 신뢰도 - 틱수: {tick_count}, 방향: {direction}, 신뢰도: {confidence:.2f}")
            return confidence
            
        except Exception as e:
            logger.error(f"틱 신뢰도 계산 오류: {e}")
            return 0.0
    
    def get_current_tick_status(self, market_data: MarketData) -> Dict[str, Any]:
        """현재 틱 상태 반환 (GUI 표시용)"""
        if not self.base_price:
            return {"status": "no_base_price", "tick_count": 0}
        
        current_tick_change = self._calculate_tick_change(market_data.current_price)
        
        # 신호 상태 판단
        if self.immediate_entry:
            signal_status = "immediate_ready"
        elif abs(current_tick_change) >= self.tick_threshold:
            signal_status = "threshold_reached"
        else:
            signal_status = "monitoring"
        
        return {
            "status": signal_status,
            "base_price": self.base_price,
            "current_price": market_data.current_price,
            "tick_count": current_tick_change,
            "threshold": self.tick_threshold,
            "progress_percentage": (abs(current_tick_change) / self.tick_threshold) * 100 if self.tick_threshold > 0 else 0
        }
    
    def reset_base_price(self, new_base_price: Optional[float] = None) -> None:
        """기준가 리셋 (수동 호출용)"""
        if new_base_price:
            self.base_price = new_base_price
        else:
            self.base_price = None
        
        self.tick_count = 0
        logger.info(f"{self.name}: 기준가 리셋 - {self.base_price}")
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """설정 업데이트"""
        super().update_config(new_config)
        
        # 호가 감시 특화 설정 업데이트
        self.tick_threshold = self.config.get("tick_threshold", self.tick_threshold)
        self.direction = self.config.get("direction", self.direction)
        self.immediate_entry = self.config.get("immediate_entry", self.immediate_entry)
        self.tick_size = self.config.get("tick_size", self.tick_size)
        
        logger.info(f"{self.name} 설정 업데이트: 임계값={self.tick_threshold}, 방향={self.direction}")
    
    def get_status(self) -> Dict[str, Any]:
        """상태 정보 반환"""
        status = super().get_status()
        status.update({
            "tick_threshold": self.tick_threshold,
            "direction": self.direction,
            "immediate_entry": self.immediate_entry,
            "base_price": self.base_price,
            "current_tick_count": self.tick_count
        })
        return status
    
    def __str__(self) -> str:
        """문자열 표현"""
        return f"호가 감시 조건 (임계값: {self.tick_threshold}틱, 방향: {self.direction})"


class AdvancedOrderbookCondition(EntryCondition):
    """고급 호가창 분석 조건"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("고급 호가창 조건", config)
        
        # 고급 설정
        self.volume_threshold = config.get("volume_threshold", 1000000)  # 볼륨 임계값
        self.spread_analysis = config.get("spread_analysis", True)  # 스프레드 분석
        self.depth_analysis = config.get("depth_analysis", True)  # 호가 깊이 분석
        
        # 호가창 데이터 히스토리
        self.orderbook_history = []
        self.max_history = config.get("max_history", 10)
        
        logger.info(f"고급 호가창 조건 초기화: 볼륨임계값={self.volume_threshold}")
    
    def evaluate(self, market_data: MarketData, position: Optional[Position] = None) -> Optional[Signal]:
        """고급 호가창 조건 평가"""
        try:
            if not self.is_active() or not self._validate_market_data(market_data):
                return None
            
            # 호가창 데이터 수집 (실제로는 API에서 받아와야 함)
            orderbook_data = self._get_orderbook_data(market_data)
            if not orderbook_data:
                return None
            
            # 호가창 히스토리 업데이트
            self._update_orderbook_history(orderbook_data)
            
            # 고급 분석 수행
            signal = self._analyze_orderbook_patterns(market_data, orderbook_data)
            
            self._update_evaluation_stats(signal)
            return signal
            
        except Exception as e:
            logger.error(f"{self.name} 평가 오류: {e}")
            return None
    
    def _get_orderbook_data(self, market_data: MarketData) -> Optional[Dict[str, Any]]:
        """호가창 데이터 수집 (모의 데이터)"""
        # 실제 구현에서는 거래소 API에서 호가창 데이터를 받아와야 함
        # 여기서는 시뮬레이션용 데이터 생성
        current_price = market_data.current_price
        
        return {
            "bids": [  # 매수 호가
                {"price": current_price - 0.5, "quantity": 10.5},
                {"price": current_price - 1.0, "quantity": 25.2},
                {"price": current_price - 1.5, "quantity": 15.8},
            ],
            "asks": [  # 매도 호가
                {"price": current_price + 0.5, "quantity": 8.3},
                {"price": current_price + 1.0, "quantity": 20.1},
                {"price": current_price + 1.5, "quantity": 12.7},
            ],
            "timestamp": market_data.timestamp
        }
    
    def _update_orderbook_history(self, orderbook_data: Dict[str, Any]) -> None:
        """호가창 히스토리 업데이트"""
        self.orderbook_history.append(orderbook_data)
        
        # 최대 히스토리 크기 유지
        if len(self.orderbook_history) > self.max_history:
            self.orderbook_history.pop(0)
    
    def _analyze_orderbook_patterns(self, market_data: MarketData, orderbook_data: Dict[str, Any]) -> Optional[Signal]:
        """호가창 패턴 분석"""
        try:
            # 스프레드 분석
            if self.spread_analysis:
                spread_signal = self._analyze_spread(market_data, orderbook_data)
                if spread_signal:
                    return spread_signal
            
            # 호가 깊이 분석
            if self.depth_analysis:
                depth_signal = self._analyze_depth_imbalance(market_data, orderbook_data)
                if depth_signal:
                    return depth_signal
            
            return None
            
        except Exception as e:
            logger.error(f"호가창 패턴 분석 오류: {e}")
            return None
    
    def _analyze_spread(self, market_data: MarketData, orderbook_data: Dict[str, Any]) -> Optional[Signal]:
        """스프레드 분석"""
        try:
            bids = orderbook_data["bids"]
            asks = orderbook_data["asks"]
            
            if not bids or not asks:
                return None
            
            best_bid = max(bids, key=lambda x: x["price"])["price"]
            best_ask = min(asks, key=lambda x: x["price"])["price"]
            
            spread = best_ask - best_bid
            spread_percentage = (spread / market_data.current_price) * 100
            
            # 스프레드가 비정상적으로 넓으면 변동성 증가 신호
            if spread_percentage > 0.1:  # 0.1% 이상
                confidence = min(spread_percentage / 0.2, 0.8)  # 최대 80%
                
                return self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.BUY.value,  # 변동성 증가 시 매수 (예시)
                    confidence=confidence,
                    metadata={
                        "analysis_type": "spread",
                        "spread": spread,
                        "spread_percentage": spread_percentage,
                        "best_bid": best_bid,
                        "best_ask": best_ask
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"스프레드 분석 오류: {e}")
            return None
    
    def _analyze_depth_imbalance(self, market_data: MarketData, orderbook_data: Dict[str, Any]) -> Optional[Signal]:
        """호가 깊이 불균형 분석"""
        try:
            bids = orderbook_data["bids"]
            asks = orderbook_data["asks"]
            
            # 총 매수/매도 물량 계산
            total_bid_quantity = sum(bid["quantity"] for bid in bids)
            total_ask_quantity = sum(ask["quantity"] for ask in asks)
            
            if total_bid_quantity + total_ask_quantity == 0:
                return None
            
            # 불균형 비율 계산
            imbalance_ratio = (total_bid_quantity - total_ask_quantity) / (total_bid_quantity + total_ask_quantity)
            
            # 불균형이 클 때 신호 생성
            if abs(imbalance_ratio) > 0.3:  # 30% 이상 불균형
                signal_type = SignalType.BUY if imbalance_ratio > 0 else SignalType.SELL
                confidence = min(abs(imbalance_ratio), 0.9)
                
                return self._create_signal(
                    market_data=market_data,
                    signal_type=signal_type.value,
                    confidence=confidence,
                    metadata={
                        "analysis_type": "depth_imbalance",
                        "imbalance_ratio": imbalance_ratio,
                        "total_bid_quantity": total_bid_quantity,
                        "total_ask_quantity": total_ask_quantity
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"호가 깊이 분석 오류: {e}")
            return None
