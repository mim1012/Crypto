"""
데이터 모델 정의 모듈

이 모듈은 시스템에서 사용되는 모든 데이터 모델을 정의합니다.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SignalType(Enum):
    """신호 타입"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """주문 타입"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"


class OrderStatus(Enum):
    """주문 상태"""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PositionSide(Enum):
    """포지션 방향"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class MarketData:
    """시장 데이터"""
    symbol: str
    current_price: float
    close_prices: List[float]
    high_prices: List[float]
    low_prices: List[float]
    volume: float = 0.0
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp()))

    @property
    def last_price(self) -> float:
        """current_price의 별칭 (backward compatibility)"""
        return self.current_price
    
    def __post_init__(self):
        """초기화 후 검증"""
        if not self.symbol:
            raise ValueError("심볼은 필수입니다")
        if self.current_price <= 0:
            raise ValueError("현재가는 0보다 커야 합니다")
        if len(self.close_prices) == 0:
            raise ValueError("종가 데이터는 필수입니다")
    
    def get_latest_close(self) -> float:
        """최신 종가 반환"""
        return self.close_prices[-1] if self.close_prices else self.current_price
    
    def get_price_change(self) -> float:
        """가격 변화율 반환 (%)"""
        if len(self.close_prices) < 2:
            return 0.0
        
        prev_price = self.close_prices[-2]
        current_price = self.close_prices[-1]
        
        return ((current_price - prev_price) / prev_price) * 100
    
    def get_moving_average(self, period: int) -> Optional[float]:
        """이동평균 계산"""
        if len(self.close_prices) < period:
            return None
        
        return sum(self.close_prices[-period:]) / period
    
    def get_price_channel(self, period: int) -> Optional[Dict[str, float]]:
        """Price Channel 계산"""
        if len(self.high_prices) < period or len(self.low_prices) < period:
            return None
        
        return {
            "upper": max(self.high_prices[-period:]),
            "lower": min(self.low_prices[-period:])
        }


@dataclass
class Signal:
    """거래 신호"""
    type: SignalType
    symbol: str
    price: float
    confidence: float
    source: str
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 검증"""
        if not isinstance(self.type, SignalType):
            if isinstance(self.type, str):
                self.type = SignalType(self.type)
            else:
                raise ValueError("신호 타입이 올바르지 않습니다")
        
        if not self.symbol:
            raise ValueError("심볼은 필수입니다")
        if self.price <= 0:
            raise ValueError("가격은 0보다 커야 합니다")
        if not 0 <= self.confidence <= 1:
            raise ValueError("신뢰도는 0-1 사이여야 합니다")
    
    def to_order(self, quantity: float, order_type: OrderType = OrderType.MARKET) -> 'Order':
        """신호를 주문으로 변환"""
        return Order(
            symbol=self.symbol,
            side=self.type.value,
            quantity=quantity,
            order_type=order_type,
            price=self.price if order_type == OrderType.LIMIT else None
        )
    
    def is_buy_signal(self) -> bool:
        """매수 신호인지 확인"""
        return self.type == SignalType.BUY
    
    def is_sell_signal(self) -> bool:
        """매도 신호인지 확인"""
        return self.type == SignalType.SELL


@dataclass
class Order:
    """주문"""
    symbol: str
    side: str
    quantity: float
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"
    client_order_id: Optional[str] = None
    reduce_only: bool = False
    close_position: bool = False
    
    def __post_init__(self):
        """초기화 후 검증"""
        if not self.symbol:
            raise ValueError("심볼은 필수입니다")
        if self.side not in ["BUY", "SELL"]:
            raise ValueError("주문 방향은 BUY 또는 SELL이어야 합니다")
        if self.quantity <= 0:
            raise ValueError("수량은 0보다 커야 합니다")
        
        if not isinstance(self.order_type, OrderType):
            if isinstance(self.order_type, str):
                self.order_type = OrderType(self.order_type)
    
    def is_market_order(self) -> bool:
        """시장가 주문인지 확인"""
        return self.order_type == OrderType.MARKET
    
    def is_limit_order(self) -> bool:
        """지정가 주문인지 확인"""
        return self.order_type == OrderType.LIMIT
    
    def requires_price(self) -> bool:
        """가격이 필요한 주문인지 확인"""
        return self.order_type in [OrderType.LIMIT, OrderType.STOP]


@dataclass
class OrderResult:
    """주문 결과"""
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: Optional[float]
    status: OrderStatus
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    commission: float = 0.0
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    
    def __post_init__(self):
        """초기화 후 검증"""
        if not isinstance(self.status, OrderStatus):
            if isinstance(self.status, str):
                self.status = OrderStatus(self.status)
    
    def is_filled(self) -> bool:
        """주문이 체결되었는지 확인"""
        return self.status == OrderStatus.FILLED
    
    def is_partially_filled(self) -> bool:
        """부분 체결되었는지 확인"""
        return self.status == OrderStatus.PARTIALLY_FILLED
    
    def get_fill_percentage(self) -> float:
        """체결률 반환"""
        if self.quantity == 0:
            return 0.0
        return (self.filled_quantity / self.quantity) * 100


@dataclass
class Position:
    """포지션"""
    symbol: str
    side: PositionSide
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    leverage: int = 1
    margin: float = 0.0
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    
    def __post_init__(self):
        """초기화 후 검증"""
        if not isinstance(self.side, PositionSide):
            if isinstance(self.side, str):
                self.side = PositionSide(self.side)
        
        if self.size < 0:
            raise ValueError("포지션 크기는 0 이상이어야 합니다")
        if self.entry_price <= 0:
            raise ValueError("진입가는 0보다 커야 합니다")
        if self.current_price <= 0:
            raise ValueError("현재가는 0보다 커야 합니다")
    
    def calculate_pnl(self) -> float:
        """PnL 계산"""
        if self.size == 0:
            return 0.0
        
        if self.side == PositionSide.LONG:
            return (self.current_price - self.entry_price) * self.size
        else:  # SHORT
            return (self.entry_price - self.current_price) * self.size
    
    def calculate_pnl_percentage(self) -> float:
        """PnL 비율 계산 (%)"""
        if self.entry_price == 0:
            return 0.0
        
        pnl = self.calculate_pnl()
        invested_amount = self.entry_price * self.size
        
        return (pnl / invested_amount) * 100
    
    def is_long(self) -> bool:
        """롱 포지션인지 확인"""
        return self.side == PositionSide.LONG
    
    def is_short(self) -> bool:
        """숏 포지션인지 확인"""
        return self.side == PositionSide.SHORT
    
    def update_current_price(self, price: float):
        """현재가 업데이트"""
        self.current_price = price
        self.unrealized_pnl = self.calculate_pnl()


@dataclass
class AccountInfo:
    """계좌 정보"""
    balance: float
    available_balance: float
    used_margin: float = 0.0
    free_margin: float = 0.0
    total_pnl: float = 0.0
    positions: List[Position] = field(default_factory=list)
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    
    def __post_init__(self):
        """초기화 후 계산"""
        if self.free_margin == 0.0:
            self.free_margin = self.available_balance - self.used_margin
    
    def get_total_position_value(self) -> float:
        """총 포지션 가치 계산"""
        return sum(pos.current_price * pos.size for pos in self.positions)
    
    def get_total_unrealized_pnl(self) -> float:
        """총 미실현 PnL 계산"""
        return sum(pos.unrealized_pnl for pos in self.positions)
    
    def get_margin_ratio(self) -> float:
        """마진 비율 계산"""
        if self.balance == 0:
            return 0.0
        return (self.used_margin / self.balance) * 100
    
    def can_open_position(self, required_margin: float) -> bool:
        """포지션 개설 가능 여부 확인"""
        return self.free_margin >= required_margin


@dataclass
class TradingStats:
    """거래 통계"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_commission: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    start_time: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    end_time: Optional[int] = None
    
    def update_stats(self, pnl: float, commission: float):
        """통계 업데이트"""
        self.total_trades += 1
        self.total_pnl += pnl
        self.total_commission += commission
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # 승률 계산
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
    
    def get_average_pnl(self) -> float:
        """평균 PnL 계산"""
        if self.total_trades == 0:
            return 0.0
        return self.total_pnl / self.total_trades
    
    def get_net_profit(self) -> float:
        """순이익 계산"""
        return self.total_pnl - self.total_commission


@dataclass
class SystemStatus:
    """시스템 상태"""
    is_running: bool = False
    is_trading_enabled: bool = False
    connected_exchanges: List[str] = field(default_factory=list)
    active_positions: int = 0
    last_update: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    error_message: Optional[str] = None
    
    def update_status(self, **kwargs):
        """상태 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.last_update = int(datetime.now().timestamp())
    
    def is_healthy(self) -> bool:
        """시스템이 정상인지 확인"""
        return (self.is_running and 
                len(self.connected_exchanges) > 0 and 
                self.error_message is None)
    
    def get_uptime(self) -> int:
        """가동 시간 반환 (초)"""
        return int(datetime.now().timestamp()) - self.last_update
