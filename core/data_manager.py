"""
실시간 데이터 관리자 모듈

이 모듈은 실시간 시장 데이터를 관리하고 배포합니다.
"""

import asyncio
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json

from utils.logger import get_logger
from core.event_system import publish_event, EventType

logger = get_logger(__name__)


@dataclass
class TickData:
    """틱 데이터 클래스"""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    exchange: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'price': self.price,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat(),
            'exchange': self.exchange
        }


@dataclass
class KlineData:
    """캔들 데이터 클래스"""
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    exchange: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'interval': self.interval,
            'open_time': self.open_time.isoformat(),
            'close_time': self.close_time.isoformat(),
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'close_price': self.close_price,
            'volume': self.volume,
            'exchange': self.exchange
        }


@dataclass
class OrderBookData:
    """호가 데이터 클래스"""
    symbol: str
    bids: List[List[float]]  # [[price, quantity], ...]
    asks: List[List[float]]  # [[price, quantity], ...]
    timestamp: datetime
    exchange: str = ""
    
    def get_best_bid(self) -> Optional[float]:
        """최고 매수 호가"""
        return self.bids[0][0] if self.bids else None
    
    def get_best_ask(self) -> Optional[float]:
        """최저 매도 호가"""
        return self.asks[0][0] if self.asks else None
    
    def get_spread(self) -> Optional[float]:
        """스프레드"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'bids': self.bids,
            'asks': self.asks,
            'timestamp': self.timestamp.isoformat(),
            'exchange': self.exchange
        }


class DataBuffer:
    """데이터 버퍼 클래스"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.data = deque(maxlen=max_size)
        self.lock = threading.Lock()
    
    def add(self, item: Any) -> None:
        """데이터 추가"""
        with self.lock:
            self.data.append(item)
    
    def get_latest(self, count: int = 1) -> List[Any]:
        """최신 데이터 반환"""
        with self.lock:
            if count == 1:
                return [self.data[-1]] if self.data else []
            else:
                return list(self.data)[-count:] if len(self.data) >= count else list(self.data)
    
    def get_all(self) -> List[Any]:
        """모든 데이터 반환"""
        with self.lock:
            return list(self.data)
    
    def clear(self) -> None:
        """버퍼 클리어"""
        with self.lock:
            self.data.clear()


class MarketDataManager:
    """시장 데이터 관리자"""
    
    def __init__(self):
        self.running = False
        self.subscribers: Dict[str, List[Callable]] = {}
        
        # 데이터 버퍼들
        self.tick_buffers: Dict[str, DataBuffer] = {}  # symbol -> DataBuffer
        self.kline_buffers: Dict[str, Dict[str, DataBuffer]] = {}  # symbol -> interval -> DataBuffer
        self.orderbook_buffers: Dict[str, DataBuffer] = {}  # symbol -> DataBuffer
        
        # 현재 가격 캐시
        self.current_prices: Dict[str, float] = {}
        
        # 시뮬레이션 데이터
        self.simulation_thread = None
        self.simulation_running = False
        
        logger.info("시장 데이터 관리자 초기화 완료")
    
    def start(self) -> None:
        """데이터 관리자 시작"""
        if not self.running:
            self.running = True
            self.start_simulation()
            logger.info("시장 데이터 관리자 시작됨")
    
    def stop(self) -> None:
        """데이터 관리자 중지"""
        if self.running:
            self.running = False
            self.stop_simulation()
            logger.info("시장 데이터 관리자 중지됨")
    
    def subscribe(self, data_type: str, callback: Callable) -> None:
        """데이터 구독"""
        if data_type not in self.subscribers:
            self.subscribers[data_type] = []
        
        if callback not in self.subscribers[data_type]:
            self.subscribers[data_type].append(callback)
            logger.debug(f"데이터 구독 등록: {data_type}")
    
    def unsubscribe(self, data_type: str, callback: Callable) -> None:
        """데이터 구독 해제"""
        if data_type in self.subscribers:
            if callback in self.subscribers[data_type]:
                self.subscribers[data_type].remove(callback)
                logger.debug(f"데이터 구독 해제: {data_type}")
    
    def _notify_subscribers(self, data_type: str, data: Any) -> None:
        """구독자들에게 데이터 알림"""
        if data_type in self.subscribers:
            for callback in self.subscribers[data_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"구독자 알림 오류: {e}")
    
    def add_tick_data(self, tick_data: TickData) -> None:
        """틱 데이터 추가"""
        symbol = tick_data.symbol
        
        # 버퍼 생성 (없는 경우)
        if symbol not in self.tick_buffers:
            self.tick_buffers[symbol] = DataBuffer(1000)
        
        # 데이터 추가
        self.tick_buffers[symbol].add(tick_data)
        
        # 현재가 업데이트
        self.current_prices[symbol] = tick_data.price
        
        # 구독자들에게 알림
        self._notify_subscribers('tick', tick_data)
        
        # 이벤트 발행
        publish_event(EventType.PRICE_UPDATE, tick_data.to_dict(), "DataManager")
    
    def add_kline_data(self, kline_data: KlineData) -> None:
        """캔들 데이터 추가"""
        symbol = kline_data.symbol
        interval = kline_data.interval
        
        # 버퍼 생성 (없는 경우)
        if symbol not in self.kline_buffers:
            self.kline_buffers[symbol] = {}
        if interval not in self.kline_buffers[symbol]:
            self.kline_buffers[symbol][interval] = DataBuffer(500)
        
        # 데이터 추가
        self.kline_buffers[symbol][interval].add(kline_data)
        
        # 구독자들에게 알림
        self._notify_subscribers('kline', kline_data)
        
        # 이벤트 발행
        publish_event(EventType.KLINE_UPDATE, kline_data.to_dict(), "DataManager")
    
    def add_orderbook_data(self, orderbook_data: OrderBookData) -> None:
        """호가 데이터 추가"""
        symbol = orderbook_data.symbol
        
        # 버퍼 생성 (없는 경우)
        if symbol not in self.orderbook_buffers:
            self.orderbook_buffers[symbol] = DataBuffer(100)
        
        # 데이터 추가
        self.orderbook_buffers[symbol].add(orderbook_data)
        
        # 구독자들에게 알림
        self._notify_subscribers('orderbook', orderbook_data)
        
        # 이벤트 발행
        publish_event(EventType.ORDERBOOK_UPDATE, orderbook_data.to_dict(), "DataManager")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 반환"""
        return self.current_prices.get(symbol)
    
    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """최신 틱 데이터 반환"""
        if symbol in self.tick_buffers:
            latest = self.tick_buffers[symbol].get_latest(1)
            return latest[0] if latest else None
        return None
    
    def get_latest_kline(self, symbol: str, interval: str) -> Optional[KlineData]:
        """최신 캔들 데이터 반환"""
        if symbol in self.kline_buffers and interval in self.kline_buffers[symbol]:
            latest = self.kline_buffers[symbol][interval].get_latest(1)
            return latest[0] if latest else None
        return None
    
    def get_kline_history(self, symbol: str, interval: str, count: int = 100) -> List[KlineData]:
        """캔들 히스토리 반환"""
        if symbol in self.kline_buffers and interval in self.kline_buffers[symbol]:
            return self.kline_buffers[symbol][interval].get_latest(count)
        return []
    
    def get_latest_orderbook(self, symbol: str) -> Optional[OrderBookData]:
        """최신 호가 데이터 반환"""
        if symbol in self.orderbook_buffers:
            latest = self.orderbook_buffers[symbol].get_latest(1)
            return latest[0] if latest else None
        return None
    
    def calculate_moving_average(self, symbol: str, interval: str, period: int) -> Optional[float]:
        """이동평균 계산"""
        klines = self.get_kline_history(symbol, interval, period)
        if len(klines) >= period:
            # 최근 period개의 종가로 이동평균 계산
            close_prices = [kline.close_price for kline in klines[-period:]]
            return sum(close_prices) / len(close_prices)
        return None
    
    def calculate_price_channel(self, symbol: str, interval: str, period: int) -> Optional[Dict[str, float]]:
        """Price Channel 계산"""
        klines = self.get_kline_history(symbol, interval, period)
        if len(klines) >= period:
            recent_klines = klines[-period:]
            high_prices = [kline.high_price for kline in recent_klines]
            low_prices = [kline.low_price for kline in recent_klines]
            
            return {
                'upper': max(high_prices),
                'lower': min(low_prices),
                'middle': (max(high_prices) + min(low_prices)) / 2
            }
        return None
    
    def start_simulation(self) -> None:
        """시뮬레이션 데이터 생성 시작"""
        if not self.simulation_running:
            self.simulation_running = True
            self.simulation_thread = threading.Thread(target=self._simulation_worker, daemon=True)
            self.simulation_thread.start()
            logger.info("시뮬레이션 데이터 생성 시작")
    
    def stop_simulation(self) -> None:
        """시뮬레이션 데이터 생성 중지"""
        if self.simulation_running:
            self.simulation_running = False
            if self.simulation_thread:
                self.simulation_thread.join(timeout=1.0)
            logger.info("시뮬레이션 데이터 생성 중지")
    
    def _simulation_worker(self) -> None:
        """시뮬레이션 데이터 생성 워커"""
        import random
        
        # 기본 가격 설정
        base_prices = {
            'BTCUSDT': 50000.0,
            'ETHUSDT': 3000.0,
            'ADAUSDT': 0.5
        }
        
        current_prices = base_prices.copy()
        last_kline_time = {}
        
        while self.simulation_running:
            try:
                current_time = datetime.now()
                
                for symbol, base_price in base_prices.items():
                    # 틱 데이터 생성
                    price_change = random.uniform(-0.01, 0.01) * base_price
                    new_price = current_prices[symbol] + price_change
                    current_prices[symbol] = max(new_price, base_price * 0.8)  # 최소 20% 하락 제한
                    
                    tick_data = TickData(
                        symbol=symbol,
                        price=current_prices[symbol],
                        volume=random.uniform(0.1, 10.0),
                        timestamp=current_time,
                        exchange="simulation"
                    )
                    self.add_tick_data(tick_data)
                    
                    # 1분마다 캔들 데이터 생성
                    if symbol not in last_kline_time or \
                       (current_time - last_kline_time[symbol]).total_seconds() >= 60:
                        
                        open_price = current_prices[symbol]
                        high_price = open_price * random.uniform(1.0, 1.02)
                        low_price = open_price * random.uniform(0.98, 1.0)
                        close_price = random.uniform(low_price, high_price)
                        
                        kline_data = KlineData(
                            symbol=symbol,
                            interval="1m",
                            open_time=current_time - timedelta(minutes=1),
                            close_time=current_time,
                            open_price=open_price,
                            high_price=high_price,
                            low_price=low_price,
                            close_price=close_price,
                            volume=random.uniform(100, 1000),
                            exchange="simulation"
                        )
                        self.add_kline_data(kline_data)
                        last_kline_time[symbol] = current_time
                    
                    # 호가 데이터 생성
                    current_price = current_prices[symbol]
                    tick_size = 1.0 if current_price > 1000 else 0.01
                    
                    bids = []
                    asks = []
                    
                    for i in range(5):
                        bid_price = current_price - (i + 1) * tick_size
                        ask_price = current_price + (i + 1) * tick_size
                        bid_qty = random.uniform(0.1, 5.0)
                        ask_qty = random.uniform(0.1, 5.0)
                        
                        bids.append([bid_price, bid_qty])
                        asks.append([ask_price, ask_qty])
                    
                    orderbook_data = OrderBookData(
                        symbol=symbol,
                        bids=bids,
                        asks=asks,
                        timestamp=current_time,
                        exchange="simulation"
                    )
                    self.add_orderbook_data(orderbook_data)
                
                time.sleep(1)  # 1초마다 업데이트
                
            except Exception as e:
                logger.error(f"시뮬레이션 데이터 생성 오류: {e}")
                time.sleep(1)


# 전역 데이터 관리자 인스턴스
_data_manager = None


def get_data_manager() -> MarketDataManager:
    """전역 데이터 관리자 반환"""
    global _data_manager
    if _data_manager is None:
        _data_manager = MarketDataManager()
    return _data_manager


def start_data_manager() -> None:
    """데이터 관리자 시작"""
    data_manager = get_data_manager()
    data_manager.start()


def stop_data_manager() -> None:
    """데이터 관리자 중지"""
    data_manager = get_data_manager()
    data_manager.stop()
