"""
바이비트 선물 거래 API 클라이언트

이 모듈은 바이비트 선물 거래소 API를 구현합니다.
"""

import hashlib
import hmac
import time
import json
import requests
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlencode

from api.base_api import (
    BaseExchangeAPI, APICredentials, OrderRequest, OrderResponse, 
    PositionInfo, AccountInfo, TickerInfo, KlineData,
    OrderType, OrderSide, OrderStatus, APIError, RateLimitError
)
from utils.logger import get_logger

logger = get_logger(__name__)


class BybitFuturesClient(BaseExchangeAPI):
    """바이비트 선물 거래 클라이언트"""
    
    def __init__(self, credentials: APICredentials):
        # 바이비트 선물 API 엔드포인트를 먼저 설정
        if credentials.testnet:
            base_url = "https://api-testnet.bybit.com"
        else:
            base_url = "https://api.bybit.com"

        # 부모 클래스 초기화
        super().__init__(credentials)

        # base_url 재설정
        self.base_url = base_url
        
        # 바이비트 특화 설정
        self.max_calls_per_minute = 600  # 바이비트 요청 제한
        self.recv_window = 5000  # 요청 유효 시간 (밀리초)
        
        # 심볼 정보 캐시
        self.symbol_info_cache = {}
        self.cache_update_time = 0
        
        logger.info(f"바이비트 선물 클라이언트 초기화 완료 (테스트넷: {credentials.testnet})")
    
    def get_exchange_name(self) -> str:
        """거래소 이름 반환"""
        return "Bybit Futures"
    
    def _prepare_headers(self, method: str, endpoint: str, params: Dict[str, Any]) -> Dict[str, str]:
        """바이비트 요청 헤더 준비 (호환성 유지)"""
        _, headers, _ = self._prepare_request(method, endpoint, params, signed=True)
        return headers

    def get_timestamp(self) -> int:
        """현재 타임스탬프 반환 (밀리초)"""
        return int(time.time() * 1000)

    def _generate_signature(self, params_str: str, timestamp: str, recv_window: str) -> str:
        """바이비트 API 서명 생성"""
        # 바이비트 V5 API 서명 방식
        param_str = timestamp + self.credentials.api_key + recv_window + params_str
        signature = hmac.new(
            self.credentials.secret_key.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _prepare_request(self, method: str, endpoint: str, params: Dict[str, Any], signed: bool = False) -> Tuple[str, Dict[str, str], Any]:
        """바이비트 요청 준비"""
        headers = {'Content-Type': 'application/json'}

        if signed:
            timestamp = str(self.get_timestamp())
            recv_window = str(self.recv_window)

            # 파라미터 문자열 생성
            if method.upper() in ["POST", "PUT", "DELETE"]:
                params_str = json.dumps(params, separators=(',', ':')) if params else ""
                request_data = params  # POST는 JSON body로 전송
            else:
                params_str = urlencode(sorted(params.items())) if params else ""
                request_data = params  # GET은 query params로 전송

            # 서명 생성
            signature = self._generate_signature(params_str, timestamp, recv_window)

            # 헤더 추가
            headers.update({
                'X-BAPI-API-KEY': self.credentials.api_key,
                'X-BAPI-SIGN': signature,
                'X-BAPI-SIGN-TYPE': '2',
                'X-BAPI-TIMESTAMP': timestamp,
                'X-BAPI-RECV-WINDOW': recv_window
            })
        else:
            request_data = params

        url = f"{self.base_url}{endpoint}"
        return url, headers, request_data

    def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, signed: bool = False) -> Dict[str, Any]:
        """바이비트 API 요청 실행"""
        try:
            if params is None:
                params = {}

            # 요청 준비
            url, headers, request_data = self._prepare_request(method, endpoint, params, signed)

            # 요청 실행
            if method.upper() == "GET":
                response = self.session.get(url, params=request_data, headers=headers, timeout=30)
            elif method.upper() in ["POST", "PUT", "DELETE"]:
                response = self.session.request(
                    method.upper(),
                    url,
                    json=request_data,
                    headers=headers,
                    timeout=30
                )
            else:
                raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")

            # 응답 처리
            response.raise_for_status()
            result = response.json()

            # 바이비트 응답 코드 확인
            if result.get('retCode') != 0:
                error_msg = result.get('retMsg', 'Unknown error')
                logger.error(f"바이비트 API 오류: {error_msg}")
                raise APIError(f"API 오류: {error_msg}")

            return result

        except requests.exceptions.HTTPError as e:
            logger.error(f"바이비트 HTTP 오류: {e}, Response: {e.response.text if e.response else 'N/A'}")
            raise APIError(f"HTTP 오류: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"바이비트 요청 오류: {e}")
            raise APIError(f"요청 실패: {e}")
        except Exception as e:
            logger.error(f"바이비트 요청 처리 오류: {e}")
            raise
    
    def test_connectivity(self) -> bool:
        """연결 테스트"""
        try:
            response = self._make_request("GET", "/v5/market/time")
            return response.get("retCode") == 0
        except Exception as e:
            logger.error(f"바이비트 연결 테스트 실패: {e}")
            return False
    
    def get_server_time(self) -> int:
        """서버 시간 조회"""
        try:
            response = self._make_request("GET", "/v5/market/time")
            if response.get("retCode") == 0:
                return int(response["result"]["timeSecond"]) * 1000  # 밀리초로 변환
            else:
                raise APIError(f"서버 시간 조회 실패: {response.get('retMsg')}")
        except Exception as e:
            logger.error(f"바이비트 서버 시간 조회 실패: {e}")
            raise APIError(f"서버 시간 조회 실패: {e}")
    
    def get_account_info(self) -> AccountInfo:
        """계좌 정보 조회"""
        try:
            # 계좌 잔고 조회
            balance_response = self._make_request("GET", "/v5/account/wallet-balance", 
                                                {"accountType": "UNIFIED"}, signed=True)
            
            if balance_response.get("retCode") != 0:
                raise APIError(f"계좌 정보 조회 실패: {balance_response.get('retMsg')}")
            
            # 포지션 정보 조회
            positions = self.get_positions()
            
            # 잔고 정보 파싱
            wallet_data = balance_response["result"]["list"][0] if balance_response["result"]["list"] else {}
            
            total_balance = 0.0
            available_balance = 0.0
            unrealized_pnl = 0.0
            
            for coin_data in wallet_data.get("coin", []):
                if coin_data["coin"] == "USDT":  # USDT 기준
                    total_balance = float(coin_data["walletBalance"])
                    available_balance = float(coin_data["availableToWithdraw"])
                    unrealized_pnl = float(coin_data["unrealisedPnl"])
                    break
            
            # 사용 중인 마진 계산
            used_margin = sum(pos.margin for pos in positions)
            
            account_info = AccountInfo(
                total_balance=total_balance,
                available_balance=available_balance,
                used_margin=used_margin,
                unrealized_pnl=unrealized_pnl,
                total_margin_balance=total_balance + unrealized_pnl,
                positions=positions,
                timestamp=time.time()
            )
            
            return account_info
            
        except Exception as e:
            logger.error(f"바이비트 계좌 정보 조회 실패: {e}")
            raise APIError(f"계좌 정보 조회 실패: {e}")
    
    def get_positions(self) -> List[PositionInfo]:
        """포지션 목록 조회"""
        try:
            params = {
                "category": "linear",  # USDT 선물
                "settleCoin": "USDT"
            }
            
            response = self._make_request("GET", "/v5/position/list", params, signed=True)
            
            if response.get("retCode") != 0:
                raise APIError(f"포지션 조회 실패: {response.get('retMsg')}")
            
            positions = []
            for pos_data in response["result"]["list"]:
                size = float(pos_data["size"])
                if size > 0:  # 포지션이 있는 경우만
                    position = PositionInfo(
                        symbol=pos_data["symbol"],
                        side=pos_data["side"],  # "Buy" or "Sell"
                        size=size,
                        entry_price=float(pos_data["avgPrice"]),
                        mark_price=float(pos_data["markPrice"]),
                        unrealized_pnl=float(pos_data["unrealisedPnl"]),
                        percentage=float(pos_data["unrealisedPnl"]) / float(pos_data["positionValue"]) * 100 if float(pos_data["positionValue"]) > 0 else 0,
                        leverage=int(float(pos_data["leverage"])),
                        margin=float(pos_data["positionIM"]),  # Initial Margin
                        timestamp=time.time()
                    )
                    positions.append(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"바이비트 포지션 조회 실패: {e}")
            raise APIError(f"포지션 조회 실패: {e}")
    
    def get_ticker(self, symbol: str) -> TickerInfo:
        """티커 정보 조회"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol
            }
            
            response = self._make_request("GET", "/v5/market/tickers", params)
            
            if response.get("retCode") != 0:
                raise APIError(f"티커 조회 실패: {response.get('retMsg')}")
            
            ticker_data = response["result"]["list"][0] if response["result"]["list"] else {}
            
            ticker = TickerInfo(
                symbol=ticker_data["symbol"],
                price=float(ticker_data["lastPrice"]),
                bid_price=float(ticker_data["bid1Price"]),
                ask_price=float(ticker_data["ask1Price"]),
                volume_24h=float(ticker_data["volume24h"]),
                change_24h=float(ticker_data["price24hPcnt"]) * float(ticker_data["lastPrice"]) / 100,
                change_percent_24h=float(ticker_data["price24hPcnt"]),
                high_24h=float(ticker_data["highPrice24h"]),
                low_24h=float(ticker_data["lowPrice24h"]),
                timestamp=time.time()
            )
            
            return ticker
            
        except Exception as e:
            logger.error(f"바이비트 티커 조회 실패 ({symbol}): {e}")
            raise APIError(f"티커 조회 실패: {e}")
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500, 
                   start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[KlineData]:
        """캔들 데이터 조회"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "interval": self._convert_interval(interval),
                "limit": min(limit, 1000)  # 바이비트 최대 제한
            }
            
            if start_time:
                params["start"] = start_time
            if end_time:
                params["end"] = end_time
            
            response = self._make_request("GET", "/v5/market/kline", params)
            
            if response.get("retCode") != 0:
                raise APIError(f"캔들 데이터 조회 실패: {response.get('retMsg')}")
            
            klines = []
            for kline_data in response["result"]["list"]:
                kline = KlineData(
                    symbol=symbol,
                    open_time=int(kline_data[0]),
                    close_time=int(kline_data[0]) + self._get_interval_ms(interval) - 1,
                    open_price=float(kline_data[1]),
                    high_price=float(kline_data[2]),
                    low_price=float(kline_data[3]),
                    close_price=float(kline_data[4]),
                    volume=float(kline_data[5]),
                    quote_volume=float(kline_data[6]),
                    trades_count=0,  # 바이비트는 제공하지 않음
                    interval=interval
                )
                klines.append(kline)
            
            # 바이비트는 최신순으로 반환하므로 시간순으로 정렬
            klines.reverse()
            return klines
            
        except Exception as e:
            logger.error(f"바이비트 캔들 데이터 조회 실패 ({symbol}): {e}")
            raise APIError(f"캔들 데이터 조회 실패: {e}")
    
    def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """주문 생성"""
        try:
            # 바이비트 주문 파라미터 구성
            params = {
                "category": "linear",
                "symbol": order_request.symbol,
                "side": self._convert_order_side(order_request.side),
                "orderType": self._convert_order_type(order_request.order_type),
                "qty": str(order_request.quantity)
            }
            
            # 주문 타입별 추가 파라미터
            if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
                if order_request.price is None:
                    raise ValueError("지정가 주문에는 가격이 필요합니다")
                params["price"] = str(order_request.price)
            
            if order_request.order_type in [OrderType.STOP_MARKET, OrderType.STOP_LIMIT]:
                if order_request.stop_price is None:
                    raise ValueError("스톱 주문에는 스톱 가격이 필요합니다")
                params["stopLoss"] = str(order_request.stop_price)
            
            if order_request.reduce_only:
                params["reduceOnly"] = True
            
            if order_request.close_position:
                params["closeOnTrigger"] = True
            
            # 시간 조건
            if order_request.time_in_force:
                params["timeInForce"] = order_request.time_in_force
            
            # 주문 실행
            response = self._make_request("POST", "/v5/order/create", params, signed=True)
            
            if response.get("retCode") != 0:
                raise APIError(f"주문 생성 실패: {response.get('retMsg')}")
            
            # 응답 파싱
            result = response["result"]
            order_response = OrderResponse(
                order_id=result["orderId"],
                client_order_id=result["orderLinkId"],
                symbol=order_request.symbol,
                side=order_request.side,
                order_type=order_request.order_type,
                quantity=order_request.quantity,
                price=order_request.price,
                status=OrderStatus.NEW,  # 바이비트는 생성 시 NEW 상태
                filled_quantity=0.0,
                avg_price=None,
                timestamp=time.time()
            )
            
            logger.info(f"바이비트 주문 생성 성공: {order_response.order_id}")
            return order_response
            
        except Exception as e:
            logger.error(f"바이비트 주문 생성 실패: {e}")
            raise APIError(f"주문 생성 실패: {e}")
    
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """주문 취소"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "orderId": order_id
            }
            
            response = self._make_request("POST", "/v5/order/cancel", params, signed=True)
            
            success = response.get("retCode") == 0
            if success:
                logger.info(f"바이비트 주문 취소 성공: {order_id}")
            else:
                logger.error(f"바이비트 주문 취소 실패: {response.get('retMsg')}")
            
            return success
            
        except Exception as e:
            logger.error(f"바이비트 주문 취소 실패 ({order_id}): {e}")
            return False
    
    def get_order_status(self, symbol: str, order_id: str) -> OrderResponse:
        """주문 상태 조회"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "orderId": order_id
            }
            
            response = self._make_request("GET", "/v5/order/realtime", params, signed=True)
            
            if response.get("retCode") != 0:
                raise APIError(f"주문 상태 조회 실패: {response.get('retMsg')}")
            
            order_data = response["result"]["list"][0] if response["result"]["list"] else {}
            
            order_response = OrderResponse(
                order_id=order_data["orderId"],
                client_order_id=order_data["orderLinkId"],
                symbol=order_data["symbol"],
                side=OrderSide.BUY if order_data["side"] == "Buy" else OrderSide.SELL,
                order_type=self._convert_bybit_order_type(order_data["orderType"]),
                quantity=float(order_data["qty"]),
                price=float(order_data["price"]) if order_data["price"] else None,
                status=self._convert_order_status(order_data["orderStatus"]),
                filled_quantity=float(order_data["cumExecQty"]),
                avg_price=float(order_data["avgPrice"]) if order_data["avgPrice"] else None,
                timestamp=int(order_data["updatedTime"])
            )
            
            return order_response
            
        except Exception as e:
            logger.error(f"바이비트 주문 상태 조회 실패 ({order_id}): {e}")
            raise APIError(f"주문 상태 조회 실패: {e}")
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """미체결 주문 조회"""
        try:
            params = {
                "category": "linear"
            }
            
            if symbol:
                params["symbol"] = symbol
            
            response = self._make_request("GET", "/v5/order/realtime", params, signed=True)
            
            if response.get("retCode") != 0:
                raise APIError(f"미체결 주문 조회 실패: {response.get('retMsg')}")
            
            orders = []
            for order_data in response["result"]["list"]:
                order = OrderResponse(
                    order_id=order_data["orderId"],
                    client_order_id=order_data["orderLinkId"],
                    symbol=order_data["symbol"],
                    side=OrderSide.BUY if order_data["side"] == "Buy" else OrderSide.SELL,
                    order_type=self._convert_bybit_order_type(order_data["orderType"]),
                    quantity=float(order_data["qty"]),
                    price=float(order_data["price"]) if order_data["price"] else None,
                    status=self._convert_order_status(order_data["orderStatus"]),
                    filled_quantity=float(order_data["cumExecQty"]),
                    avg_price=float(order_data["avgPrice"]) if order_data["avgPrice"] else None,
                    timestamp=int(order_data["updatedTime"])
                )
                orders.append(order)
            
            return orders
            
        except Exception as e:
            logger.error(f"바이비트 미체결 주문 조회 실패: {e}")
            raise APIError(f"미체결 주문 조회 실패: {e}")
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """레버리지 설정"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "buyLeverage": str(leverage),
                "sellLeverage": str(leverage)
            }
            
            response = self._make_request("POST", "/v5/position/set-leverage", params, signed=True)
            
            success = response.get("retCode") == 0
            if success:
                logger.info(f"바이비트 레버리지 설정 성공: {symbol} = {leverage}배")
            else:
                logger.error(f"바이비트 레버리지 설정 실패: {response.get('retMsg')}")
            
            return success
            
        except Exception as e:
            logger.error(f"바이비트 레버리지 설정 실패 ({symbol}): {e}")
            return False
    
    def set_margin_mode(self, symbol: str, margin_mode: str) -> bool:
        """마진 모드 설정"""
        try:
            # 바이비트는 포지션 모드 설정 (0: 양방향, 3: 단방향)
            mode_value = "3" if margin_mode == "ISOLATED" else "0"
            
            params = {
                "category": "linear",
                "symbol": symbol,
                "mode": mode_value
            }
            
            response = self._make_request("POST", "/v5/position/switch-mode", params, signed=True)
            
            success = response.get("retCode") == 0
            if success:
                logger.info(f"바이비트 포지션 모드 설정 성공: {symbol} = {margin_mode}")
            else:
                logger.error(f"바이비트 포지션 모드 설정 실패: {response.get('retMsg')}")
            
            return success
            
        except Exception as e:
            logger.error(f"바이비트 포지션 모드 설정 실패 ({symbol}): {e}")
            return False
    
    # 바이비트 특화 메서드들
    def _convert_order_type(self, order_type: OrderType) -> str:
        """주문 타입을 바이비트 형식으로 변환"""
        type_mapping = {
            OrderType.MARKET: "Market",
            OrderType.LIMIT: "Limit",
            OrderType.STOP_MARKET: "Market",  # 스톱 로스와 함께 사용
            OrderType.STOP_LIMIT: "Limit",   # 스톱 로스와 함께 사용
            OrderType.TAKE_PROFIT_MARKET: "Market",  # 테이크 프로핏과 함께 사용
            OrderType.TAKE_PROFIT_LIMIT: "Limit"     # 테이크 프로핏과 함께 사용
        }
        return type_mapping.get(order_type, "Market")
    
    def _convert_order_side(self, side: OrderSide) -> str:
        """주문 방향을 바이비트 형식으로 변환"""
        return "Buy" if side == OrderSide.BUY else "Sell"
    
    def _convert_bybit_order_type(self, bybit_type: str) -> OrderType:
        """바이비트 주문 타입을 내부 형식으로 변환"""
        type_mapping = {
            "Market": OrderType.MARKET,
            "Limit": OrderType.LIMIT
        }
        return type_mapping.get(bybit_type, OrderType.MARKET)
    
    def _convert_order_status(self, bybit_status: str) -> OrderStatus:
        """바이비트 주문 상태를 내부 형식으로 변환"""
        status_mapping = {
            "New": OrderStatus.NEW,
            "PartiallyFilled": OrderStatus.PARTIALLY_FILLED,
            "Filled": OrderStatus.FILLED,
            "Cancelled": OrderStatus.CANCELED,
            "Rejected": OrderStatus.REJECTED,
            "Deactivated": OrderStatus.EXPIRED
        }
        return status_mapping.get(bybit_status, OrderStatus.NEW)
    
    def _convert_interval(self, interval: str) -> str:
        """인터벌을 바이비트 형식으로 변환"""
        # 바이낸스 형식을 바이비트 형식으로 변환
        interval_mapping = {
            "1m": "1",
            "3m": "3", 
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "2h": "120",
            "4h": "240",
            "6h": "360",
            "12h": "720",
            "1d": "D",
            "1w": "W",
            "1M": "M"
        }
        return interval_mapping.get(interval, "1")
    
    def _get_interval_ms(self, interval: str) -> int:
        """인터벌을 밀리초로 변환"""
        interval_ms = {
            "1m": 60 * 1000,
            "3m": 3 * 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "30m": 30 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "2h": 2 * 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "6h": 6 * 60 * 60 * 1000,
            "12h": 12 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000,
            "1w": 7 * 24 * 60 * 60 * 1000,
            "1M": 30 * 24 * 60 * 60 * 1000
        }
        return interval_ms.get(interval, 60 * 1000)
    
    def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """바이비트 거래 수수료 조회"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol
            }
            
            response = self._make_request("GET", "/v5/account/fee-rate", params, signed=True)
            
            if response.get("retCode") == 0:
                fee_data = response["result"]["list"][0] if response["result"]["list"] else {}
                return {
                    "maker_fee": float(fee_data.get("makerFeeRate", "0.0001")),
                    "taker_fee": float(fee_data.get("takerFeeRate", "0.0006"))
                }
            
        except Exception as e:
            logger.error(f"바이비트 수수료 조회 실패 ({symbol}): {e}")
        
        # 기본 수수료 반환
        return {
            "maker_fee": 0.0001,  # 0.01%
            "taker_fee": 0.0006   # 0.06%
        }
    
    def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """펀딩 수수료 조회"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol
            }
            
            response = self._make_request("GET", "/v5/market/funding/history", params)
            
            if response.get("retCode") == 0 and response["result"]["list"]:
                funding_data = response["result"]["list"][0]
                return {
                    "symbol": funding_data["symbol"],
                    "funding_rate": float(funding_data["fundingRate"]),
                    "funding_time": int(funding_data["fundingRateTimestamp"]),
                    "timestamp": time.time()
                }
            
        except Exception as e:
            logger.error(f"바이비트 펀딩 수수료 조회 실패 ({symbol}): {e}")
        
        return {
            "symbol": symbol,
            "funding_rate": 0.0,
            "funding_time": 0,
            "timestamp": time.time()
        }
    
    def __str__(self) -> str:
        """문자열 표현"""
        testnet_str = " (테스트넷)" if self.credentials.testnet else ""
        return f"바이비트 선물 API 클라이언트{testnet_str}"
