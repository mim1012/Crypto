"""
거래소 API 기본 클래스

이 모듈은 모든 거래소 API의 기본 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import hashlib
import hmac
import requests
from utils.logger import get_logger

logger = get_logger(__name__)


class OrderType(Enum):
    """주문 타입"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"


class OrderSide(Enum):
    """주문 방향"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """주문 상태"""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class APICredentials:
    """API 인증 정보"""
    api_key: str
    secret_key: str
    testnet: bool = False
    passphrase: Optional[str] = None  # 일부 거래소에서 사용


@dataclass
class OrderRequest:
    """주문 요청"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # Good Till Canceled
    reduce_only: bool = False
    close_position: bool = False


@dataclass
class OrderResponse:
    """주문 응답"""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float]
    status: OrderStatus
    filled_quantity: float = 0.0
    avg_price: Optional[float] = None
    timestamp: float = 0.0
    commission: float = 0.0
    commission_asset: str = ""


@dataclass
class PositionInfo:
    """포지션 정보"""
    symbol: str
    side: str  # "LONG" or "SHORT"
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    percentage: float
    leverage: int
    margin: float
    timestamp: float

    @property
    def pnl_percentage(self) -> float:
        """percentage의 별칭 (backward compatibility)"""
        return self.percentage


@dataclass
class AccountInfo:
    """계좌 정보"""
    total_balance: float
    available_balance: float
    used_margin: float
    unrealized_pnl: float
    total_margin_balance: float
    positions: List[PositionInfo]
    timestamp: float


@dataclass
class TickerInfo:
    """티커 정보"""
    symbol: str
    price: float
    bid_price: float
    ask_price: float
    volume_24h: float
    change_24h: float
    change_percent_24h: float
    high_24h: float
    low_24h: float
    timestamp: float


@dataclass
class KlineData:
    """캔들 데이터"""
    symbol: str
    open_time: float
    close_time: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    quote_volume: float
    trades_count: int
    interval: str


class BaseExchangeAPI(ABC):
    """거래소 API 기본 클래스"""
    
    def __init__(self, credentials: APICredentials):
        self.credentials = credentials
        self.base_url = ""
        self.session = requests.Session()
        self.rate_limit_calls = []  # 요청 제한 추적
        self.max_calls_per_minute = 1200  # 기본값
        
        # 공통 헤더 설정
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CryptoTradingSystem/1.0'
        })
        
        logger.info(f"{self.__class__.__name__} 초기화 완료")
    
    @abstractmethod
    def get_exchange_name(self) -> str:
        """거래소 이름 반환"""
        pass
    
    @abstractmethod
    def _generate_signature(self, params: str, timestamp: str) -> str:
        """API 서명 생성"""
        pass
    
    @abstractmethod
    def _prepare_headers(self, method: str, endpoint: str, params: Dict[str, Any]) -> Dict[str, str]:
        """요청 헤더 준비"""
        pass
    
    def _check_rate_limit(self) -> bool:
        """요청 제한 확인"""
        current_time = time.time()
        
        # 1분 이전 요청 제거
        self.rate_limit_calls = [call_time for call_time in self.rate_limit_calls 
                                if current_time - call_time < 60]
        
        # 요청 제한 확인
        if len(self.rate_limit_calls) >= self.max_calls_per_minute:
            logger.warning(f"{self.get_exchange_name()}: 요청 제한 도달")
            return False
        
        # 현재 요청 시간 추가
        self.rate_limit_calls.append(current_time)
        return True
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                     signed: bool = False) -> Dict[str, Any]:
        """API 요청 실행"""
        try:
            # 요청 제한 확인
            if not self._check_rate_limit():
                raise Exception("요청 제한 초과")
            
            # 파라미터 준비
            if params is None:
                params = {}
            
            # URL 구성
            url = f"{self.base_url}{endpoint}"
            
            # 헤더 준비
            headers = self._prepare_headers(method, endpoint, params) if signed else {}
            
            # 요청 실행
            if method.upper() == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=params, headers=headers, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=params, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=params, headers=headers, timeout=30)
            else:
                raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
            
            # 응답 처리
            response.raise_for_status()
            
            try:
                return response.json()
            except ValueError:
                logger.error(f"JSON 파싱 실패: {response.text}")
                raise Exception("응답 JSON 파싱 실패")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"{self.get_exchange_name()} API 요청 오류: {e}")
            raise Exception(f"API 요청 실패: {e}")
        except Exception as e:
            logger.error(f"{self.get_exchange_name()} 요청 처리 오류: {e}")
            raise
    
    # 공통 API 메서드들
    @abstractmethod
    def test_connectivity(self) -> bool:
        """연결 테스트"""
        pass
    
    @abstractmethod
    def get_server_time(self) -> int:
        """서버 시간 조회"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """계좌 정보 조회"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[PositionInfo]:
        """포지션 목록 조회"""
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> TickerInfo:
        """티커 정보 조회"""
        pass
    
    @abstractmethod
    def get_klines(self, symbol: str, interval: str, limit: int = 500, 
                   start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[KlineData]:
        """캔들 데이터 조회"""
        pass
    
    @abstractmethod
    def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """주문 생성"""
        pass
    
    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """주문 취소"""
        pass
    
    @abstractmethod
    def get_order_status(self, symbol: str, order_id: str) -> OrderResponse:
        """주문 상태 조회"""
        pass
    
    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """미체결 주문 조회"""
        pass
    
    @abstractmethod
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """레버리지 설정"""
        pass
    
    @abstractmethod
    def set_margin_mode(self, symbol: str, margin_mode: str) -> bool:
        """마진 모드 설정 (ISOLATED/CROSSED)"""
        pass
    
    # 유틸리티 메서드들
    def get_timestamp(self) -> int:
        """현재 타임스탬프 (밀리초)"""
        return int(time.time() * 1000)
    
    def format_symbol(self, base: str, quote: str) -> str:
        """심볼 포맷팅 (거래소별로 오버라이드)"""
        return f"{base}{quote}"
    
    def validate_symbol(self, symbol: str) -> bool:
        """심볼 유효성 검사"""
        try:
            ticker = self.get_ticker(symbol)
            return ticker is not None
        except Exception:
            return False
    
    def calculate_quantity(self, symbol: str, usdt_amount: float, price: Optional[float] = None) -> float:
        """USDT 금액을 기반으로 수량 계산"""
        try:
            if price is None:
                ticker = self.get_ticker(symbol)
                price = ticker.price
            
            quantity = usdt_amount / price
            
            # 거래소별 최소 수량 및 정밀도 적용 (서브클래스에서 구현)
            return self._round_quantity(symbol, quantity)
            
        except Exception as e:
            logger.error(f"수량 계산 오류: {e}")
            raise
    
    def _round_quantity(self, symbol: str, quantity: float) -> float:
        """수량 반올림 (거래소별로 오버라이드)"""
        # 기본적으로 소수점 6자리까지
        return round(quantity, 6)
    
    def _round_price(self, symbol: str, price: float) -> float:
        """가격 반올림 (거래소별로 오버라이드)"""
        # 기본적으로 소수점 2자리까지
        return round(price, 2)
    
    def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """거래 수수료 조회 (거래소별로 구현)"""
        return {
            "maker_fee": 0.0002,  # 0.02%
            "taker_fee": 0.0004   # 0.04%
        }
    
    def get_position_by_symbol(self, symbol: str) -> Optional[PositionInfo]:
        """특정 심볼의 포지션 조회"""
        try:
            positions = self.get_positions()
            for position in positions:
                if position.symbol == symbol and position.size != 0:
                    return position
            return None
        except Exception as e:
            logger.error(f"포지션 조회 오류: {e}")
            return None
    
    def close_position(self, symbol: str, percentage: float = 100.0) -> Optional[OrderResponse]:
        """포지션 청산"""
        try:
            position = self.get_position_by_symbol(symbol)
            if not position:
                logger.warning(f"청산할 포지션 없음: {symbol}")
                return None
            
            # 청산 수량 계산
            close_quantity = abs(position.size) * (percentage / 100.0)
            
            # 청산 주문 방향 (포지션과 반대)
            close_side = OrderSide.SELL if position.side == "LONG" else OrderSide.BUY
            
            # 시장가 청산 주문
            order_request = OrderRequest(
                symbol=symbol,
                side=close_side,
                order_type=OrderType.MARKET,
                quantity=close_quantity,
                reduce_only=True
            )
            
            return self.place_order(order_request)
            
        except Exception as e:
            logger.error(f"포지션 청산 오류: {e}")
            raise
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """모든 주문 취소"""
        try:
            open_orders = self.get_open_orders(symbol)
            canceled_count = 0
            
            for order in open_orders:
                try:
                    if self.cancel_order(order.symbol, order.order_id):
                        canceled_count += 1
                except Exception as e:
                    logger.error(f"주문 취소 실패 ({order.order_id}): {e}")
            
            logger.info(f"주문 취소 완료: {canceled_count}개")
            return canceled_count
            
        except Exception as e:
            logger.error(f"전체 주문 취소 오류: {e}")
            return 0
    
    def __str__(self) -> str:
        """문자열 표현"""
        return f"{self.get_exchange_name()} API Client"


class APIError(Exception):
    """API 오류 클래스"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 status_code: Optional[int] = None):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.message = message
    
    def __str__(self) -> str:
        if self.error_code:
            return f"API Error [{self.error_code}]: {self.message}"
        return f"API Error: {self.message}"


class RateLimitError(APIError):
    """요청 제한 오류"""
    pass


class AuthenticationError(APIError):
    """인증 오류"""
    pass


class InsufficientBalanceError(APIError):
    """잔고 부족 오류"""
    pass


class InvalidSymbolError(APIError):
    """잘못된 심볼 오류"""
    pass


class OrderError(APIError):
    """주문 오류"""
    pass
