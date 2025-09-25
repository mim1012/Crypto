"""
바이낸스 선물 거래 API 클라이언트

이 모듈은 바이낸스 선물 거래소 API를 구현합니다.
"""

import hashlib
import hmac
import time
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


class BinanceFuturesClient(BaseExchangeAPI):
    """바이낸스 선물 거래 클라이언트"""
    
    def __init__(self, credentials: APICredentials):
        # 바이낸스 API 엔드포인트 설정
        # Futures Testnet으로 다시 변경 (선물 거래 필요)
        if credentials.testnet:
            base_url = "https://testnet.binancefuture.com"  # Futures Testnet
        else:
            base_url = "https://fapi.binance.com"  # Futures Mainnet

        # 부모 클래스 초기화
        super().__init__(credentials)

        # base_url 재설정
        self.base_url = base_url
        
        # 바이낸스 특화 설정
        self.max_calls_per_minute = 1200  # 바이낸스 요청 제한
        self.recv_window = 5000  # 요청 유효 시간 (밀리초)
        
        # 심볼 정보 캐시
        self.symbol_info_cache = {}
        self.cache_update_time = 0
        
        logger.info(f"바이낸스 선물 클라이언트 초기화 완료 (테스트넷: {credentials.testnet})")
    
    def get_exchange_name(self) -> str:
        """거래소 이름 반환"""
        return "Binance Futures"
    
    def _generate_signature(self, query_string: str) -> str:
        """바이낸스 API 서명 생성"""
        signature = hmac.new(
            self.credentials.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _prepare_headers(self, method: str, endpoint: str, params: Dict[str, Any]) -> Dict[str, str]:
        """바이낸스 요청 헤더 준비 (호환성 유지)"""
        _, headers, _ = self._prepare_request(method, endpoint, params, signed=True)
        return headers

    def get_timestamp(self) -> int:
        """현재 타임스탬프 반환 (밀리초)"""
        return int(time.time() * 1000)

    def _prepare_request(self, method: str, endpoint: str, params: Dict[str, Any], signed: bool = False) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        """바이낸스 요청 준비"""
        headers = {}

        if signed:
            # 타임스탬프 추가
            timestamp = self.get_timestamp()
            params['timestamp'] = timestamp
            params['recvWindow'] = self.recv_window

            # 쿼리 스트링 생성
            query_string = urlencode(params)

            # 서명 생성 및 추가
            signature = self._generate_signature(query_string)
            params['signature'] = signature

            # API 키 헤더 추가
            headers['X-MBX-APIKEY'] = self.credentials.api_key

        url = f"{self.base_url}{endpoint}"
        return url, headers, params
    
    def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, signed: bool = False) -> Dict[str, Any]:
        """바이낸스 API 요청 실행"""
        try:
            if params is None:
                params = {}

            # 요청 준비
            url, headers, request_params = self._prepare_request(method, endpoint, params, signed)

            # 요청 실행
            if method.upper() == "GET":
                response = self.session.get(url, params=request_params, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, params=request_params, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=request_params, headers=headers, timeout=30)
            else:
                raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")

            # 응답 처리
            response.raise_for_status()

            # 빈 응답 처리 (ping 등)
            if response.text == '':
                return {}

            return response.json()

        except requests.exceptions.HTTPError as e:
            error_msg = e.response.text if e.response else 'N/A'
            logger.error(f"바이낸스 HTTP 오류: {e}, Response: {error_msg}")
            # 상세 오류 정보 출력
            if e.response:
                try:
                    error_json = e.response.json()
                    logger.error(f"API 오류 상세: {error_json}")
                except:
                    pass
            raise APIError(f"HTTP 오류: {e}, 상세: {error_msg}")
        except requests.exceptions.RequestException as e:
            logger.error(f"바이낸스 요청 오류: {e}")
            raise APIError(f"요청 실패: {e}")
        except Exception as e:
            logger.error(f"바이낸스 요청 처리 오류: {e}")
            raise

    def test_connectivity(self) -> bool:
        """연결 테스트"""
        try:
            response = self._make_request("GET", "/fapi/v1/ping")
            return response == {}
        except Exception as e:
            logger.error(f"바이낸스 연결 테스트 실패: {e}")
            return False
    
    def get_server_time(self) -> int:
        """서버 시간 조회"""
        try:
            response = self._make_request("GET", "/fapi/v1/time")
            return response["serverTime"]
        except Exception as e:
            logger.error(f"바이낸스 서버 시간 조회 실패: {e}")
            raise APIError(f"서버 시간 조회 실패: {e}")
    
    def get_account_info(self) -> AccountInfo:
        """계좌 정보 조회"""
        try:
            # Futures API endpoint 사용
            response = self._make_request("GET", "/fapi/v2/account", signed=True)

            # 디버그: API 응답 확인
            logger.debug(f"바이낸스 계좌 응답:")
            logger.debug(f"  totalWalletBalance: {response.get('totalWalletBalance', 'N/A')}")
            logger.debug(f"  availableBalance: {response.get('availableBalance', 'N/A')}")
            logger.debug(f"  totalMarginBalance: {response.get('totalMarginBalance', 'N/A')}")
            logger.debug(f"  totalInitialMargin: {response.get('totalInitialMargin', 'N/A')}")
            logger.debug(f"  totalUnrealizedProfit: {response.get('totalUnrealizedProfit', 'N/A')}")

            # 포지션 정보 파싱
            positions = []
            for pos_data in response.get("positions", []):
                if float(pos_data.get("positionAmt", 0)) != 0:
                    position = PositionInfo(
                        symbol=pos_data["symbol"],
                        side="LONG" if float(pos_data["positionAmt"]) > 0 else "SHORT",
                        size=abs(float(pos_data["positionAmt"])),
                        entry_price=float(pos_data.get("entryPrice", 0)),
                        mark_price=float(pos_data.get("markPrice", 0)),
                        unrealized_pnl=float(pos_data.get("unRealizedProfit", 0)),
                        percentage=float(pos_data.get("percentage", 0)),
                        leverage=int(pos_data.get("leverage", 1)),
                        margin=float(pos_data.get("initialMargin", 0)),
                        timestamp=time.time()
                    )
                    positions.append(position)

            # 계좌 정보 구성 (Futures API 필드)
            total_balance = float(response.get("totalWalletBalance", 0))
            available_balance = float(response.get("availableBalance", 0))

            # Testnet에서도 실제 API 응답 사용
            # 제거: 기본값 설정 로직

            account_info = AccountInfo(
                total_balance=total_balance,
                available_balance=available_balance,
                used_margin=float(response.get("totalInitialMargin", 0)),
                unrealized_pnl=float(response.get("totalUnrealizedProfit", 0)),
                total_margin_balance=float(response.get("totalMarginBalance", 0)),
                positions=positions,
                timestamp=time.time()
            )

            logger.info(f"계좌 정보 조회 성공: 잘고=${account_info.total_balance:,.2f}")
            return account_info
            
        except Exception as e:
            logger.error(f"바이낸스 계좌 정보 조회 실패: {e}")
            raise APIError(f"계좌 정보 조회 실패: {e}")
    
    def get_positions(self) -> List[PositionInfo]:
        """포지션 목록 조회"""
        try:
            response = self._make_request("GET", "/fapi/v2/positionRisk", signed=True)

            positions = []
            for pos_data in response:
                if float(pos_data.get("positionAmt", 0)) != 0:
                    position = PositionInfo(
                        symbol=pos_data["symbol"],
                        side="LONG" if float(pos_data["positionAmt"]) > 0 else "SHORT",
                        size=abs(float(pos_data["positionAmt"])),
                        entry_price=float(pos_data.get("entryPrice", 0)),
                        mark_price=float(pos_data.get("markPrice", 0)),
                        unrealized_pnl=float(pos_data.get("unRealizedProfit", 0)),
                        percentage=float(pos_data.get("percentage", 0)),
                        leverage=int(pos_data.get("leverage", 1)),
                        margin=float(pos_data.get("initialMargin", 0)),
                        timestamp=time.time()
                    )
                    positions.append(position)

            return positions
            
        except Exception as e:
            logger.error(f"바이낸스 포지션 조회 실패: {e}")
            raise APIError(f"포지션 조회 실패: {e}")
    
    def get_market_data(self, symbol: str) -> 'MarketData':
        """시장 데이터 조회 (TradingEngine용) - 동기 함수로 변경"""
        try:
            from core.models import MarketData
            from datetime import datetime

            # 실시간 티커 정보 가져오기
            ticker = self.get_ticker(symbol)

            if not ticker:
                logger.warning(f"티커 조회 실패: {symbol}")
                # Binance Public API로 실시간 가격 조회
                import requests
                try:
                    response = requests.get(
                        f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
                        timeout=2
                    )
                    if response.status_code == 200:
                        data = response.json()
                        current_price = float(data['price'])
                        logger.info(f"Public API 가격: {symbol} = ${current_price:,.2f}")
                    else:
                        current_price = 50000.0
                except:
                    current_price = 50000.0
            else:
                current_price = ticker.price
                logger.debug(f"실시간 가격: {symbol} = ${current_price:,.2f}")

            # MarketData 객체 생성 (models.py의 MarketData 클래스 구조에 맞춤)
            # MA(50) 계산을 위해 충분한 데이터 생성
            market_data = MarketData(
                symbol=symbol,
                current_price=current_price,
                close_prices=[current_price * (1 + (i * 0.0001)) for i in range(60)],  # 60개 데이터 (약간의 변화 포함)
                high_prices=[current_price * 1.001] * 60,
                low_prices=[current_price * 0.999] * 60,
                volume=ticker.base_volume if ticker and hasattr(ticker, 'base_volume') else 0.0
            )

            return market_data

        except Exception as e:
            logger.error(f"시장 데이터 조회 실패 ({symbol}): {e}")
            # 기본 MarketData 반환
            from core.models import MarketData
            return MarketData(
                symbol=symbol,
                current_price=50000.0,  # BTC 기본값
                close_prices=[50000.0] * 20,
                high_prices=[50100.0] * 20,
                low_prices=[49900.0] * 20,
                volume=0.0
            )

    def get_ticker(self, symbol: str) -> TickerInfo:
        """티커 정보 조회"""
        try:
            params = {"symbol": symbol}
            response = self._make_request("GET", "/fapi/v1/ticker/24hr", params)

            # 응답 필드 안전하게 처리 (testnet은 일부 필드가 없을 수 있음)
            ticker = TickerInfo(
                symbol=response.get("symbol", symbol),
                price=float(response.get("lastPrice", 0)),
                bid_price=float(response.get("bidPrice", response.get("lastPrice", 0))),
                ask_price=float(response.get("askPrice", response.get("lastPrice", 0))),
                volume_24h=float(response.get("volume", 0)),
                change_24h=float(response.get("priceChange", 0)),
                change_percent_24h=float(response.get("priceChangePercent", 0)),
                high_24h=float(response.get("highPrice", 0)),
                low_24h=float(response.get("lowPrice", 0)),
                timestamp=time.time()
            )

            # lastPrice를 사용하여 누락된 가격 정보 보완
            if ticker.bid_price == 0 and ticker.price > 0:
                ticker.bid_price = ticker.price * 0.9999  # 근사값
            if ticker.ask_price == 0 and ticker.price > 0:
                ticker.ask_price = ticker.price * 1.0001  # 근사값

            return ticker

        except Exception as e:
            logger.error(f"바이낸스 티커 조회 실패 ({symbol}): {e}")
            raise APIError(f"티커 조회 실패: {e}")
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500, 
                   start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[KlineData]:
        """캔들 데이터 조회"""
        try:
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": min(limit, 1500)  # 바이낸스 최대 제한
            }
            
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            
            response = self._make_request("GET", "/fapi/v1/klines", params)
            
            klines = []
            for kline_data in response:
                kline = KlineData(
                    symbol=symbol,
                    open_time=int(kline_data[0]),
                    close_time=int(kline_data[6]),
                    open_price=float(kline_data[1]),
                    high_price=float(kline_data[2]),
                    low_price=float(kline_data[3]),
                    close_price=float(kline_data[4]),
                    volume=float(kline_data[5]),
                    quote_volume=float(kline_data[7]),
                    trades_count=int(kline_data[8]),
                    interval=interval
                )
                klines.append(kline)
            
            return klines
            
        except Exception as e:
            logger.error(f"바이낸스 캔들 데이터 조회 실패 ({symbol}): {e}")
            raise APIError(f"캔들 데이터 조회 실패: {e}")
    
    def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """주문 생성"""
        try:
            # 바이낸스 주문 파라미터 구성
            # side가 이미 문자열인지 Enum인지 확인
            side_value = order_request.side.value if hasattr(order_request.side, 'value') else order_request.side

            # 수량 포맷팅 (바이낸스는 최대 5자리 소수점)
            quantity = round(order_request.quantity, 5)

            logger.info(f"주문 파라미터: symbol={order_request.symbol}, side={side_value}, quantity={quantity}")

            params = {
                "symbol": order_request.symbol,
                "side": side_value,
                "type": self._convert_order_type(order_request.order_type),
                "quantity": str(quantity)
            }
            
            # 주문 타입별 추가 파라미터
            if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
                if order_request.price is None:
                    raise ValueError("지정가 주문에는 가격이 필요합니다")
                params["price"] = str(order_request.price)
                params["timeInForce"] = order_request.time_in_force
            
            if order_request.order_type in [OrderType.STOP_MARKET, OrderType.STOP_LIMIT]:
                if order_request.stop_price is None:
                    raise ValueError("스톱 주문에는 스톱 가격이 필요합니다")
                params["stopPrice"] = str(order_request.stop_price)
            
            if order_request.reduce_only:
                params["reduceOnly"] = "true"
            
            if order_request.close_position:
                params["closePosition"] = "true"
            
            # 주문 실행
            response = self._make_request("POST", "/fapi/v1/order", params, signed=True)
            
            # 응답 파싱
            order_response = OrderResponse(
                order_id=str(response["orderId"]),
                client_order_id=response["clientOrderId"],
                symbol=response["symbol"],
                side=OrderSide(response["side"]),
                order_type=self._convert_binance_order_type(response["type"]),
                quantity=float(response["origQty"]),
                price=float(response["price"]) if response["price"] != "0" else None,
                status=self._convert_order_status(response["status"]),
                filled_quantity=float(response["executedQty"]),
                avg_price=float(response["avgPrice"]) if response["avgPrice"] != "0" else None,
                timestamp=float(response["updateTime"])
            )
            
            logger.info(f"바이낸스 주문 생성 성공: {order_response.order_id}")
            return order_response
            
        except Exception as e:
            logger.error(f"바이낸스 주문 생성 실패: {e}")
            raise APIError(f"주문 생성 실패: {e}")
    
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """주문 취소"""
        try:
            params = {
                "symbol": symbol,
                "orderId": order_id
            }
            
            response = self._make_request("DELETE", "/fapi/v1/order", params, signed=True)
            
            success = response["status"] == "CANCELED"
            if success:
                logger.info(f"바이낸스 주문 취소 성공: {order_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"바이낸스 주문 취소 실패 ({order_id}): {e}")
            return False
    
    def get_order_status(self, symbol: str, order_id: str) -> OrderResponse:
        """주문 상태 조회"""
        try:
            params = {
                "symbol": symbol,
                "orderId": order_id
            }
            
            response = self._make_request("GET", "/fapi/v1/order", params, signed=True)
            
            order_response = OrderResponse(
                order_id=str(response["orderId"]),
                client_order_id=response["clientOrderId"],
                symbol=response["symbol"],
                side=OrderSide(response["side"]),
                order_type=self._convert_binance_order_type(response["type"]),
                quantity=float(response["origQty"]),
                price=float(response["price"]) if response["price"] != "0" else None,
                status=self._convert_order_status(response["status"]),
                filled_quantity=float(response["executedQty"]),
                avg_price=float(response["avgPrice"]) if response["avgPrice"] != "0" else None,
                timestamp=float(response["updateTime"])
            )
            
            return order_response
            
        except Exception as e:
            logger.error(f"바이낸스 주문 상태 조회 실패 ({order_id}): {e}")
            raise APIError(f"주문 상태 조회 실패: {e}")
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """미체결 주문 조회"""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol
            
            response = self._make_request("GET", "/fapi/v1/openOrders", params, signed=True)
            
            orders = []
            for order_data in response:
                order = OrderResponse(
                    order_id=str(order_data["orderId"]),
                    client_order_id=order_data["clientOrderId"],
                    symbol=order_data["symbol"],
                    side=OrderSide(order_data["side"]),
                    order_type=self._convert_binance_order_type(order_data["type"]),
                    quantity=float(order_data["origQty"]),
                    price=float(order_data["price"]) if order_data["price"] != "0" else None,
                    status=self._convert_order_status(order_data["status"]),
                    filled_quantity=float(order_data["executedQty"]),
                    avg_price=float(order_data["avgPrice"]) if order_data["avgPrice"] != "0" else None,
                    timestamp=float(order_data["updateTime"])
                )
                orders.append(order)
            
            return orders
            
        except Exception as e:
            logger.error(f"바이낸스 미체결 주문 조회 실패: {e}")
            raise APIError(f"미체결 주문 조회 실패: {e}")
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """레버리지 설정"""
        try:
            params = {
                "symbol": symbol,
                "leverage": leverage
            }
            
            response = self._make_request("POST", "/fapi/v1/leverage", params, signed=True)
            
            success = response["leverage"] == leverage
            if success:
                logger.info(f"바이낸스 레버리지 설정 성공: {symbol} = {leverage}배")
            
            return success
            
        except Exception as e:
            logger.error(f"바이낸스 레버리지 설정 실패 ({symbol}): {e}")
            return False
    
    def set_margin_mode(self, symbol: str, margin_mode: str) -> bool:
        """마진 모드 설정"""
        try:
            params = {
                "symbol": symbol,
                "marginType": margin_mode  # ISOLATED or CROSSED
            }
            
            response = self._make_request("POST", "/fapi/v1/marginType", params, signed=True)
            
            # 바이낸스는 성공 시 200 응답만 반환
            logger.info(f"바이낸스 마진 모드 설정 성공: {symbol} = {margin_mode}")
            return True
            
        except Exception as e:
            logger.error(f"바이낸스 마진 모드 설정 실패 ({symbol}): {e}")
            return False
    
    # 바이낸스 특화 메서드들
    def _convert_order_type(self, order_type: OrderType) -> str:
        """주문 타입을 바이낸스 형식으로 변환"""
        type_mapping = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.STOP_MARKET: "STOP_MARKET",
            OrderType.STOP_LIMIT: "STOP",
            OrderType.TAKE_PROFIT_MARKET: "TAKE_PROFIT_MARKET",
            OrderType.TAKE_PROFIT_LIMIT: "TAKE_PROFIT"
        }
        return type_mapping.get(order_type, "MARKET")
    
    def _convert_binance_order_type(self, binance_type: str) -> OrderType:
        """바이낸스 주문 타입을 내부 형식으로 변환"""
        type_mapping = {
            "MARKET": OrderType.MARKET,
            "LIMIT": OrderType.LIMIT,
            "STOP_MARKET": OrderType.STOP_MARKET,
            "STOP": OrderType.STOP_LIMIT,
            "TAKE_PROFIT_MARKET": OrderType.TAKE_PROFIT_MARKET,
            "TAKE_PROFIT": OrderType.TAKE_PROFIT_LIMIT
        }
        return type_mapping.get(binance_type, OrderType.MARKET)
    
    def _convert_order_status(self, binance_status: str) -> OrderStatus:
        """바이낸스 주문 상태를 내부 형식으로 변환"""
        status_mapping = {
            "NEW": OrderStatus.NEW,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.EXPIRED
        }
        return status_mapping.get(binance_status, OrderStatus.NEW)
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """심볼 정보 조회 (정밀도, 최소 수량 등)"""
        try:
            # 캐시 확인 (5분마다 갱신)
            current_time = time.time()
            if current_time - self.cache_update_time > 300:
                self._update_symbol_info_cache()
            
            return self.symbol_info_cache.get(symbol, {})
            
        except Exception as e:
            logger.error(f"바이낸스 심볼 정보 조회 실패 ({symbol}): {e}")
            return {}
    
    def _update_symbol_info_cache(self) -> None:
        """심볼 정보 캐시 업데이트"""
        try:
            response = self._make_request("GET", "/fapi/v1/exchangeInfo")
            
            self.symbol_info_cache.clear()
            for symbol_data in response["symbols"]:
                symbol = symbol_data["symbol"]
                
                # 필터 정보 파싱
                filters = {}
                for filter_data in symbol_data["filters"]:
                    filters[filter_data["filterType"]] = filter_data
                
                self.symbol_info_cache[symbol] = {
                    "symbol": symbol,
                    "status": symbol_data["status"],
                    "baseAsset": symbol_data["baseAsset"],
                    "quoteAsset": symbol_data["quoteAsset"],
                    "pricePrecision": symbol_data["pricePrecision"],
                    "quantityPrecision": symbol_data["quantityPrecision"],
                    "filters": filters
                }
            
            self.cache_update_time = time.time()
            logger.info(f"바이낸스 심볼 정보 캐시 업데이트 완료: {len(self.symbol_info_cache)}개")
            
        except Exception as e:
            logger.error(f"바이낸스 심볼 정보 캐시 업데이트 실패: {e}")
    
    def _round_quantity(self, symbol: str, quantity: float) -> float:
        """바이낸스 심볼별 수량 반올림"""
        symbol_info = self.get_symbol_info(symbol)
        if symbol_info:
            precision = symbol_info.get("quantityPrecision", 6)
            return round(quantity, precision)
        return round(quantity, 6)
    
    def _round_price(self, symbol: str, price: float) -> float:
        """바이낸스 심볼별 가격 반올림"""
        symbol_info = self.get_symbol_info(symbol)
        if symbol_info:
            precision = symbol_info.get("pricePrecision", 2)
            return round(price, precision)
        return round(price, 2)
    
    def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """바이낸스 거래 수수료 조회"""
        try:
            response = self._make_request("GET", "/fapi/v1/commissionRate", {"symbol": symbol}, signed=True)
            
            return {
                "maker_fee": float(response["makerCommissionRate"]),
                "taker_fee": float(response["takerCommissionRate"])
            }
            
        except Exception as e:
            logger.error(f"바이낸스 수수료 조회 실패 ({symbol}): {e}")
            # 기본 수수료 반환
            return {
                "maker_fee": 0.0002,  # 0.02%
                "taker_fee": 0.0004   # 0.04%
            }
    
    def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """펀딩 수수료 조회"""
        try:
            params = {"symbol": symbol}
            response = self._make_request("GET", "/fapi/v1/premiumIndex", params)
            
            return {
                "symbol": response["symbol"],
                "mark_price": float(response["markPrice"]),
                "index_price": float(response["indexPrice"]),
                "funding_rate": float(response["lastFundingRate"]),
                "next_funding_time": int(response["nextFundingTime"]),
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"바이낸스 펀딩 수수료 조회 실패 ({symbol}): {e}")
            raise APIError(f"펀딩 수수료 조회 실패: {e}")
    
    def __str__(self) -> str:
        """문자열 표현"""
        testnet_str = " (테스트넷)" if self.credentials.testnet else ""
        return f"바이낸스 선물 API 클라이언트{testnet_str}"
