"""
실시간 신호 처리기 모듈

이 모듈은 실시간으로 거래 신호를 처리하고 분석합니다.
"""

import threading
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from utils.logger import get_logger
from core.data_manager import get_data_manager, TickData, KlineData, OrderBookData
from core.event_system import publish_event, EventType
from config.settings_manager import get_config

logger = get_logger(__name__)


class SignalType(Enum):
    """신호 타입"""
    ENTRY_BUY = "entry_buy"
    ENTRY_SELL = "entry_sell"
    EXIT_BUY = "exit_buy"
    EXIT_SELL = "exit_sell"


@dataclass
class TradingSignal:
    """거래 신호 클래스"""
    signal_type: SignalType
    symbol: str
    price: float
    confidence: float
    reason: str
    timestamp: datetime
    exchange: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'signal_type': self.signal_type.value,
            'symbol': self.symbol,
            'price': self.price,
            'confidence': self.confidence,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat(),
            'exchange': self.exchange,
            'metadata': self.metadata
        }


class ConditionChecker:
    """조건 검사기 기본 클래스"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', False)
        self.last_check_time = None
    
    def check(self, data: Any) -> Optional[TradingSignal]:
        """조건 검사 (서브클래스에서 구현)"""
        if not self.enabled:
            return None
        
        self.last_check_time = datetime.now()
        return self._check_condition(data)
    
    def _check_condition(self, data: Any) -> Optional[TradingSignal]:
        """실제 조건 검사 로직 (서브클래스에서 구현)"""
        pass


class MovingAverageChecker(ConditionChecker):
    """이동평균 조건 검사기"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("MovingAverage", config)
        self.period = config.get('period', 20)
        self.condition = config.get('condition', 'close_above')
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.interval = config.get('interval', '1m')
    
    def _check_condition(self, data: Any) -> Optional[TradingSignal]:
        """이동평균 조건 검사"""
        try:
            data_manager = get_data_manager()
            
            # 현재가 가져오기
            current_price = data_manager.get_current_price(self.symbol)
            if not current_price:
                return None
            
            # 이동평균 계산
            ma_value = data_manager.calculate_moving_average(self.symbol, self.interval, self.period)
            if not ma_value:
                return None
            
            # 조건 검사
            signal = None
            
            if self.condition == 'close_above' and current_price > ma_value:
                signal = TradingSignal(
                    signal_type=SignalType.ENTRY_BUY,
                    symbol=self.symbol,
                    price=current_price,
                    confidence=0.7,
                    reason=f"현재가({current_price:.2f}) > 이평선({ma_value:.2f})",
                    timestamp=datetime.now(),
                    metadata={'ma_value': ma_value, 'period': self.period}
                )
            elif self.condition == 'close_below' and current_price < ma_value:
                signal = TradingSignal(
                    signal_type=SignalType.ENTRY_SELL,
                    symbol=self.symbol,
                    price=current_price,
                    confidence=0.7,
                    reason=f"현재가({current_price:.2f}) < 이평선({ma_value:.2f})",
                    timestamp=datetime.now(),
                    metadata={'ma_value': ma_value, 'period': self.period}
                )
            
            return signal
            
        except Exception as e:
            logger.error(f"이동평균 조건 검사 오류: {e}")
            return None


class PriceChannelChecker(ConditionChecker):
    """Price Channel 조건 검사기"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("PriceChannel", config)
        self.period = config.get('period', 20)
        self.condition = config.get('condition', 'upper_buy')
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.interval = config.get('interval', '1m')
        self.last_breakout = None
    
    def _check_condition(self, data: Any) -> Optional[TradingSignal]:
        """Price Channel 조건 검사"""
        try:
            data_manager = get_data_manager()
            
            # 현재가 가져오기
            current_price = data_manager.get_current_price(self.symbol)
            if not current_price:
                return None
            
            # Price Channel 계산
            pc_data = data_manager.calculate_price_channel(self.symbol, self.interval, self.period)
            if not pc_data:
                return None
            
            upper_line = pc_data['upper']
            lower_line = pc_data['lower']
            
            # 조건 검사
            signal = None
            
            if self.condition == 'upper_buy' and current_price > upper_line:
                if self.last_breakout != 'upper':
                    signal = TradingSignal(
                        signal_type=SignalType.ENTRY_BUY,
                        symbol=self.symbol,
                        price=current_price,
                        confidence=0.8,
                        reason=f"상단선 돌파: {current_price:.2f} > {upper_line:.2f}",
                        timestamp=datetime.now(),
                        metadata={'upper': upper_line, 'lower': lower_line}
                    )
                    self.last_breakout = 'upper'
            
            elif self.condition == 'lower_sell' and current_price < lower_line:
                if self.last_breakout != 'lower':
                    signal = TradingSignal(
                        signal_type=SignalType.ENTRY_SELL,
                        symbol=self.symbol,
                        price=current_price,
                        confidence=0.8,
                        reason=f"하단선 돌파: {current_price:.2f} < {lower_line:.2f}",
                        timestamp=datetime.now(),
                        metadata={'upper': upper_line, 'lower': lower_line}
                    )
                    self.last_breakout = 'lower'
            
            # 채널 내부로 돌아오면 상태 리셋
            if lower_line <= current_price <= upper_line:
                self.last_breakout = None
            
            return signal
            
        except Exception as e:
            logger.error(f"Price Channel 조건 검사 오류: {e}")
            return None


class OrderBookChecker(ConditionChecker):
    """호가 감시 조건 검사기"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("OrderBook", config)
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.tick_threshold = config.get('tick_threshold', 5)
        self.last_price = None
        self.tick_count = 0
    
    def _check_condition(self, data: Any) -> Optional[TradingSignal]:
        """호가 감시 조건 검사"""
        try:
            data_manager = get_data_manager()
            
            # 현재가 가져오기
            current_price = data_manager.get_current_price(self.symbol)
            if not current_price:
                return None
            
            # 첫 번째 가격이면 저장하고 리턴
            if self.last_price is None:
                self.last_price = current_price
                return None
            
            # 가격 변동 확인
            price_diff = current_price - self.last_price
            
            # 틱 단위 계산 (간단히 1원 단위로 가정)
            tick_size = 1.0 if current_price > 1000 else 0.01
            tick_change = abs(price_diff) / tick_size
            
            signal = None
            
            if tick_change >= self.tick_threshold:
                if price_diff > 0:  # 상승
                    signal = TradingSignal(
                        signal_type=SignalType.ENTRY_BUY,
                        symbol=self.symbol,
                        price=current_price,
                        confidence=0.6,
                        reason=f"호가 상승 감지: {tick_change:.1f}틱 상승",
                        timestamp=datetime.now(),
                        metadata={'tick_change': tick_change, 'price_diff': price_diff}
                    )
                else:  # 하락
                    signal = TradingSignal(
                        signal_type=SignalType.ENTRY_SELL,
                        symbol=self.symbol,
                        price=current_price,
                        confidence=0.6,
                        reason=f"호가 하락 감지: {tick_change:.1f}틱 하락",
                        timestamp=datetime.now(),
                        metadata={'tick_change': tick_change, 'price_diff': price_diff}
                    )
                
                self.last_price = current_price
            
            return signal
            
        except Exception as e:
            logger.error(f"호가 감시 조건 검사 오류: {e}")
            return None


class CandleStateChecker(ConditionChecker):
    """캔들 상태 조건 검사기"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("CandleState", config)
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.interval = config.get('interval', '1m')
        self.pattern = config.get('pattern', 'bullish')
        self.last_candle_time = None
    
    def _check_condition(self, data: Any) -> Optional[TradingSignal]:
        """캔들 상태 조건 검사"""
        try:
            data_manager = get_data_manager()
            
            # 최신 캔들 가져오기
            latest_kline = data_manager.get_latest_kline(self.symbol, self.interval)
            if not latest_kline:
                return None
            
            # 새로운 캔들인지 확인
            if self.last_candle_time and latest_kline.open_time <= self.last_candle_time:
                return None
            
            self.last_candle_time = latest_kline.open_time
            
            # 캔들 패턴 분석
            is_bullish = latest_kline.close_price > latest_kline.open_price
            is_bearish = latest_kline.close_price < latest_kline.open_price
            
            signal = None
            
            if self.pattern == 'bullish' and is_bullish:
                signal = TradingSignal(
                    signal_type=SignalType.ENTRY_BUY,
                    symbol=self.symbol,
                    price=latest_kline.close_price,
                    confidence=0.5,
                    reason="양봉 패턴 감지",
                    timestamp=datetime.now(),
                    metadata={'candle_type': 'bullish', 'open': latest_kline.open_price, 'close': latest_kline.close_price}
                )
            elif self.pattern == 'bearish' and is_bearish:
                signal = TradingSignal(
                    signal_type=SignalType.ENTRY_SELL,
                    symbol=self.symbol,
                    price=latest_kline.close_price,
                    confidence=0.5,
                    reason="음봉 패턴 감지",
                    timestamp=datetime.now(),
                    metadata={'candle_type': 'bearish', 'open': latest_kline.open_price, 'close': latest_kline.close_price}
                )
            
            return signal
            
        except Exception as e:
            logger.error(f"캔들 상태 조건 검사 오류: {e}")
            return None


class SignalProcessor:
    """신호 처리기 클래스"""
    
    def __init__(self):
        self.running = False
        self.checkers: List[ConditionChecker] = []
        self.signal_history: List[TradingSignal] = []
        self.signal_callbacks: List[Callable] = []
        
        # 처리 스레드
        self.processor_thread = None
        
        # 설정 로드
        self.load_config()
        
        logger.info("신호 처리기 초기화 완료")
    
    def load_config(self) -> None:
        """설정에서 조건 검사기들 로드"""
        try:
            config = get_config()
            
            # 진입 조건들 로드
            entry_config = config.entry
            
            if entry_config.ma_enabled:
                ma_checker = MovingAverageChecker({
                    'enabled': True,
                    'period': entry_config.ma_period,
                    'condition': entry_config.ma_condition,
                    'symbol': config.trading.symbol,
                    'interval': '1m'
                })
                self.checkers.append(ma_checker)
            
            if entry_config.pc_enabled:
                pc_checker = PriceChannelChecker({
                    'enabled': True,
                    'period': entry_config.pc_period,
                    'condition': entry_config.pc_condition,
                    'symbol': config.trading.symbol,
                    'interval': '1m'
                })
                self.checkers.append(pc_checker)
            
            if entry_config.orderbook_enabled:
                ob_checker = OrderBookChecker({
                    'enabled': True,
                    'symbol': config.trading.symbol,
                    'tick_threshold': 5
                })
                self.checkers.append(ob_checker)
            
            if entry_config.candle_enabled:
                candle_checker = CandleStateChecker({
                    'enabled': True,
                    'symbol': config.trading.symbol,
                    'interval': '1m',
                    'pattern': 'bullish'
                })
                self.checkers.append(candle_checker)
            
            logger.info(f"조건 검사기 {len(self.checkers)}개 로드됨")
            
        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")
    
    def start(self) -> None:
        """신호 처리기 시작"""
        if not self.running:
            self.running = True
            self.processor_thread = threading.Thread(target=self._processor_worker, daemon=True)
            self.processor_thread.start()
            logger.info("신호 처리기 시작됨")
    
    def stop(self) -> None:
        """신호 처리기 중지"""
        if self.running:
            self.running = False
            if self.processor_thread:
                self.processor_thread.join(timeout=1.0)
            logger.info("신호 처리기 중지됨")
    
    def add_signal_callback(self, callback: Callable) -> None:
        """신호 콜백 추가"""
        if callback not in self.signal_callbacks:
            self.signal_callbacks.append(callback)
    
    def remove_signal_callback(self, callback: Callable) -> None:
        """신호 콜백 제거"""
        if callback in self.signal_callbacks:
            self.signal_callbacks.remove(callback)
    
    def _processor_worker(self) -> None:
        """신호 처리 워커 스레드"""
        while self.running:
            try:
                # 모든 조건 검사기 실행
                for checker in self.checkers:
                    if checker.enabled:
                        signal = checker.check(None)
                        if signal:
                            self._process_signal(signal)
                
                time.sleep(1)  # 1초마다 검사
                
            except Exception as e:
                logger.error(f"신호 처리 오류: {e}")
                time.sleep(1)
    
    def _process_signal(self, signal: TradingSignal) -> None:
        """신호 처리"""
        try:
            # 신호 히스토리에 추가
            self.signal_history.append(signal)
            
            # 최근 100개만 유지
            if len(self.signal_history) > 100:
                self.signal_history = self.signal_history[-100:]
            
            # 로그 출력
            logger.info(f"거래 신호 생성: {signal.signal_type.value} | {signal.symbol} | {signal.reason}")
            
            # 콜백 함수들 호출
            for callback in self.signal_callbacks:
                try:
                    callback(signal)
                except Exception as e:
                    logger.error(f"신호 콜백 오류: {e}")
            
            # 이벤트 발행
            if signal.signal_type in [SignalType.ENTRY_BUY, SignalType.ENTRY_SELL]:
                publish_event(EventType.ENTRY_SIGNAL, signal.to_dict(), "SignalProcessor")
            else:
                publish_event(EventType.EXIT_SIGNAL, signal.to_dict(), "SignalProcessor")
            
        except Exception as e:
            logger.error(f"신호 처리 오류: {e}")
    
    def get_recent_signals(self, count: int = 10) -> List[TradingSignal]:
        """최근 신호들 반환"""
        return self.signal_history[-count:] if len(self.signal_history) >= count else self.signal_history
    
    def get_signal_count(self) -> int:
        """총 신호 개수 반환"""
        return len(self.signal_history)


# 전역 신호 처리기 인스턴스
_signal_processor = None


def get_signal_processor() -> SignalProcessor:
    """전역 신호 처리기 반환"""
    global _signal_processor
    if _signal_processor is None:
        _signal_processor = SignalProcessor()
    return _signal_processor


def start_signal_processor() -> None:
    """신호 처리기 시작"""
    processor = get_signal_processor()
    processor.start()


def stop_signal_processor() -> None:
    """신호 처리기 중지"""
    processor = get_signal_processor()
    processor.stop()
