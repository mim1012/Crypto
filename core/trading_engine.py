"""
거래 엔진 핵심 모듈

이 모듈은 자동매매 시스템의 핵심 거래 로직을 담당합니다.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

from core.models import (
    MarketData, Signal, Order, OrderResult, Position,
    AccountInfo, TradingStats, SystemStatus, SignalType
)
from api.base_api import OrderStatus
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from config.settings_manager import TradingConfig
from utils.logger import get_logger, get_trading_logger, get_performance_logger

logger = get_logger(__name__)
trading_logger = get_trading_logger()
perf_logger = get_performance_logger()


class TradingEngine(QObject):
    """거래 엔진 핵심 클래스"""
    
    # Qt 시그널 정의
    status_changed = pyqtSignal(dict)
    position_updated = pyqtSignal(dict)
    signal_generated = pyqtSignal(dict)
    trade_executed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self,
                 config: Any,  # TradingConfig 또는 AppConfig를 받을 수 있도록 변경
                 api_connectors: Dict[str, Any]):
        super().__init__()

        # config가 AppConfig인 경우 trading 속성 추출
        if hasattr(config, 'trading'):
            self.config = config.trading
            self.full_config = config  # 전체 설정도 저장
        else:
            # TradingConfig인 경우 그대로 사용
            self.config = config
            self.full_config = None

        self.api_connectors = api_connectors
        
        # 거래 상태
        self.is_running = False
        self.is_trading_enabled = False
        
        # 조건 관리
        self.entry_conditions = []
        self.exit_conditions = []
        self.risk_manager = None
        self.combination_mode = "OR"  # 기본값: OR (하나 이상 충족)
        
        # 포지션 및 통계
        self.positions = {}  # exchange -> List[Position]
        self.trading_stats = TradingStats()
        self.system_status = SystemStatus()
        
        # 시장 데이터 캐시
        self.market_data_cache = {}
        
        # 비동기 작업 관리
        self.trading_task = None
        self.update_task = None
        
        logger.info("거래 엔진 초기화 완료")
    
    async def start(self) -> bool:
        """거래 시작"""
        try:
            logger.info("거래 엔진 시작")

            # API 연결 확인
            connected_exchanges = await self._connect_exchanges()
            if not connected_exchanges:
                logger.warning("연결된 거래소가 없습니다 - 시뮬레이션 모드로 실행")
                connected_exchanges = ["simulation"]

            # 시스템 상태 업데이트
            self.system_status.update_status(
                is_running=True,
                connected_exchanges=connected_exchanges
            )

            # 거래 루프 시작
            self.is_running = True
            self.trading_task = asyncio.create_task(self._trading_loop())
            self.update_task = asyncio.create_task(self._update_loop())

            # 상태 변경 시그널 발송
            self.status_changed.emit(self._get_status_dict())

            logger.info(f"거래 시작 완료 - 연결된 거래소: {connected_exchanges}")
            return True

        except Exception as e:
            logger.error(f"거래 시작 실패: {e}")
            self.error_occurred.emit(str(e))
            return False

    def start_sync(self) -> bool:
        """동기식 거래 시작 (GUI용)"""
        try:
            logger.info("거래 엔진 동기식 시작")
            self.is_running = True
            self.is_trading_enabled = True

            # 백그라운드 스레드에서 거래 루프 실행
            import threading

            def run_trading_loop():
                """백그라운드 거래 루프"""
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._trading_loop())

            self.trading_thread = threading.Thread(target=run_trading_loop, daemon=True)
            self.trading_thread.start()

            logger.info("거래 루프가 백그라운드에서 시작되었습니다")
            return True

        except Exception as e:
            logger.error(f"동기식 거래 시작 실패: {e}")
            return False
    
    async def stop(self) -> None:
        """거래 중지"""
        try:
            logger.info("거래 엔진 중지")
            
            self.is_running = False
            self.is_trading_enabled = False
            
            # 비동기 작업 취소
            if self.trading_task:
                self.trading_task.cancel()
            if self.update_task:
                self.update_task.cancel()
            
            # API 연결 해제
            await self._disconnect_exchanges()
            
            # 시스템 상태 업데이트
            self.system_status.update_status(
                is_running=False,
                is_trading_enabled=False,
                connected_exchanges=[]
            )
            
            # 상태 변경 시그널 발송
            self.status_changed.emit(self._get_status_dict())
            
            logger.info("거래 엔진 중지 완료")
            
        except Exception as e:
            logger.error(f"거래 중지 실패: {e}")
    
    async def _connect_exchanges(self) -> List[str]:
        """거래소 연결"""
        connected = []

        for exchange_name, connector in self.api_connectors.items():
            try:
                perf_logger.start_timer(f"connect_{exchange_name}")

                # BinanceFuturesClient는 초기화 시 이미 연결됨
                # connect 메서드가 없으므로 test_connectivity로 연결 확인
                if hasattr(connector, 'test_connectivity'):
                    success = connector.test_connectivity()
                elif hasattr(connector, 'connect'):
                    success = await connector.connect()
                else:
                    # connect 메서드가 없으면 이미 연결된 것으로 가정
                    success = True

                if success:
                    connected.append(exchange_name)
                    logger.info(f"{exchange_name} 연결 성공")
                else:
                    logger.warning(f"{exchange_name} 연결 실패")

                perf_logger.end_timer(f"connect_{exchange_name}")

            except Exception as e:
                logger.error(f"{exchange_name} 연결 오류: {e}")
        
        return connected
    
    async def _disconnect_exchanges(self) -> None:
        """거래소 연결 해제"""
        for exchange_name, connector in self.api_connectors.items():
            try:
                # BinanceFuturesClient는 disconnect 메서드가 없음
                if hasattr(connector, 'disconnect'):
                    await connector.disconnect()
                    logger.info(f"{exchange_name} 연결 해제")
                else:
                    # disconnect 메서드가 없으면 스킵
                    logger.debug(f"{exchange_name} 연결 해제 스킵 (메서드 없음)")
            except Exception as e:
                logger.error(f"{exchange_name} 연결 해제 오류: {e}")
    
    async def _trading_loop(self) -> None:
        """메인 거래 루프"""
        logger.info("====== 거래 루프 시작 ======")
        logger.info(f"진입 조건 수: {len(self.entry_conditions)}개")
        logger.info(f"청산 조건 수: {len(self.exit_conditions)}개")
        logger.info(f"거래 활성화: {self.is_trading_enabled}")
        logger.info(f"조합 모드: {self.combination_mode}")
        logger.info("============================")
        cycle_count = 0

        while self.is_running:
            try:
                cycle_count += 1
                logger.info(f"거래 사이클 #{cycle_count} 시작")
                perf_logger.start_timer("trading_cycle")

                # 거래 사이클 실행
                await self._run_trading_cycle()

                perf_logger.end_timer("trading_cycle")
                logger.info(f"거래 사이클 #{cycle_count} 완료")

                # 1초 대기
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("거래 루프 취소됨")
                break
            except Exception as e:
                logger.error(f"거래 루프 오류: {e}")
                self.error_occurred.emit(str(e))
                await asyncio.sleep(5)  # 오류 시 5초 대기
    
    async def _update_loop(self) -> None:
        """업데이트 루프 (GUI 상태 업데이트)"""
        while self.is_running:
            try:
                # 포지션 업데이트
                await self._update_positions()
                
                # 계좌 정보 업데이트
                await self._update_account_info()
                
                # 시스템 상태 업데이트
                self._update_system_status()
                
                # 5초마다 업데이트
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"업데이트 루프 오류: {e}")
                await asyncio.sleep(10)
    
    async def _run_trading_cycle(self) -> None:
        """거래 사이클 실행"""
        if not self.is_trading_enabled:
            logger.info("⏸️ 거래가 비활성화 상태 - 사이클 스킵")
            return

        try:
            # 1. 시장 데이터 수집
            logger.info("[1/4] 시장 데이터 수집 시작...")
            await self._collect_market_data()

            # 시장 데이터 표시
            for exchange, data in self.market_data_cache.items():
                if data:
                    # MarketData의 current_price 필드 사용
                    price = data.current_price if hasattr(data, 'current_price') else 0.0
                    logger.info(f"  - {exchange}: 가격=${price:,.2f}")

            # 2. 진입 신호 확인
            if len(self.entry_conditions) == 0:
                logger.warning("[2/4] 진입 조건 없음 - 진입 조건을 설정하세요!")
            else:
                logger.info(f"[2/4] 진입 조건 평가 중... (총 {len(self.entry_conditions)}개 조건)")
                for i, condition in enumerate(self.entry_conditions, 1):
                    logger.info(f"  - 조건 {i}: {condition.get_name()} {'(활성)' if condition.is_active() else '(비활성)'}")

                entry_signals = await self._evaluate_entry_conditions()
                if entry_signals:
                    logger.info(f">>> 진입 신호 발견: {len(entry_signals)}개 <<<")
                else:
                    logger.info("  결과: 진입 신호 없음")

            # 3. 청산 신호 확인
            if len(self.exit_conditions) == 0:
                logger.warning("[3/4] 청산 조건 없음 - 청산 조건을 설정하세요!")
            else:
                logger.info(f"[3/4] 청산 조건 평가 중... (총 {len(self.exit_conditions)}개 조건)")
                for i, condition in enumerate(self.exit_conditions, 1):
                    logger.info(f"  - 조건 {i}: {condition.get_name()} {'(활성)' if condition.is_active() else '(비활성)'}")

                exit_signals = await self._evaluate_exit_conditions()
                if exit_signals:
                    logger.info(f">>> 청산 신호 발견: {len(exit_signals)}개 <<<")
                else:
                    logger.info("  결과: 청산 신호 없음")

            # 4. 신호 실행
            if 'entry_signals' in locals() and entry_signals:
                logger.info("[4/4] 진입 신호 실행 중...")
                await self._execute_signals(entry_signals, [])
            elif 'exit_signals' in locals() and exit_signals:
                logger.info("[4/4] 청산 신호 실행 중...")
                await self._execute_signals([], exit_signals)
            else:
                logger.info("[4/4] 실행할 신호 없음 - 대기")
            
        except Exception as e:
            logger.error(f"거래 사이클 오류: {e}")
            raise
    
    async def _collect_market_data(self) -> None:
        """시장 데이터 수집"""
        for exchange_name, connector in self.api_connectors.items():
            try:
                perf_logger.start_timer(f"market_data_{exchange_name}")

                # 기본 심볼 데이터 수집 (BTCUSDT)
                # connector가 get_market_data 메소드를 가지고 있는지 확인
                if hasattr(connector, 'get_market_data'):
                    # get_market_data는 이제 동기 함수임
                    if not asyncio.iscoroutinefunction(connector.get_market_data):
                        # 동기 함수인 경우 - 실시간 데이터 가져오기
                        market_data = connector.get_market_data("BTCUSDT")
                        logger.debug(f"{exchange_name} 실시간 BTC 가격: ${market_data.current_price:,.2f}")
                    else:
                        # async 함수인 경우 (구버전 호환)
                        market_data = await connector.get_market_data("BTCUSDT")
                elif hasattr(connector, 'get_ticker'):
                        # get_market_data가 없으면 티커로 대체
                        ticker = connector.get_ticker("BTCUSDT")
                        if ticker:
                            from core.models import MarketData
                            market_data = MarketData(
                                symbol="BTCUSDT",
                                exchange=exchange_name,
                                timestamp=datetime.now(),
                                last_price=ticker.price,
                                bid_price=ticker.bid_price,
                                ask_price=ticker.ask_price,
                                volume=ticker.volume,
                                high_24h=ticker.high_24h,
                                low_24h=ticker.low_24h,
                                change_24h=ticker.change_24h_percent
                            )
                        else:
                            # 티커 조회 실패 시 기본값
                            logger.warning(f"{exchange_name}: 티커 조회 실패, 기본값 사용")
                            from core.models import MarketData
                            market_data = MarketData(
                                symbol="BTCUSDT",
                                exchange=exchange_name,
                                timestamp=datetime.now(),
                                last_price=43520.00  # 기본값
                            )
                else:
                    # get_market_data 메소드가 없는 경우 티커로 대체
                    if hasattr(connector, 'get_ticker'):
                        ticker = connector.get_ticker("BTCUSDT")
                        if ticker:
                            from core.models import MarketData
                            market_data = MarketData(
                                symbol="BTCUSDT",
                                exchange=exchange_name,
                                timestamp=datetime.now(),
                                last_price=ticker.price,
                                bid_price=ticker.bid_price,
                                ask_price=ticker.ask_price,
                                volume=ticker.volume
                            )
                        else:
                            logger.warning(f"{exchange_name}: 티커 조회 실패")
                            continue
                    else:
                        logger.warning(f"{exchange_name}: get_market_data 메소드 없음")
                        continue

                self.market_data_cache[exchange_name] = market_data

                perf_logger.end_timer(f"market_data_{exchange_name}")

            except Exception as e:
                logger.error(f"{exchange_name} 시장 데이터 수집 오류: {e}")
    
    async def _evaluate_entry_conditions(self) -> List[Signal]:
        """진입 조건 평가 (AND/OR 로직 적용)"""
        all_signals = []

        if len(self.entry_conditions) == 0:
            return []

        logger.debug(f"진입 조건 평가 시작 - 조건 수: {len(self.entry_conditions)}개, 조합: {self.combination_mode}")

        for exchange_name, market_data in self.market_data_cache.items():
            condition_signals = []  # 각 조건별 신호

            # 각 조건 평가
            for condition in self.entry_conditions:
                try:
                    if condition.is_active():
                        signal = condition.evaluate(market_data)
                        if signal:
                            signal.metadata["exchange"] = exchange_name
                            signal.metadata["condition"] = condition.get_name()
                            condition_signals.append(signal)
                            logger.info(f"    ✓ 조건 충족: {condition.get_name()} - 신호 강도: {signal.confidence:.2f}")
                        else:
                            logger.debug(f"    ✗ 조건 미충족: {condition.get_name()}")

                except Exception as e:
                    logger.error(f"진입 조건 평가 오류: {condition.get_name()} - {e}")

            # AND/OR 로직 적용
            if self.combination_mode == "AND":
                # AND: 모든 활성 조건이 충족되어야 함
                active_conditions = [c for c in self.entry_conditions if c.is_active()]
                if len(condition_signals) == len(active_conditions) and len(active_conditions) > 0:
                    # 모든 조건 충족 - 가장 높은 신뢰도의 신호 사용
                    best_signal = max(condition_signals, key=lambda s: s.confidence)
                    best_signal.metadata["combination"] = "AND"

                    # 리스크 관리 검증 (risk_manager가 없으면 통과)
                    if not self.risk_manager or self.risk_manager.validate_entry_signal(best_signal):
                        all_signals.append(best_signal)
                        self._emit_signal(best_signal, exchange_name)
                        logger.info(f"AND 조건 충족: {len(condition_signals)}개 조건 모두 만족")

            else:  # OR
                # OR: 하나 이상의 조건이 충족되면 됨
                for signal in condition_signals:
                    signal.metadata["combination"] = "OR"

                    # 리스크 관리 검증 (risk_manager가 없으면 통과)
                    if not self.risk_manager or self.risk_manager.validate_entry_signal(signal):
                        all_signals.append(signal)
                        self._emit_signal(signal, exchange_name)
                        logger.info(f"OR 조건 충족: {signal.metadata['condition']}")

        return all_signals

    def _emit_signal(self, signal, exchange_name):
        """신호 발송"""
        # 신호 로그
        trading_logger.log_signal(
            signal.type.value,
            signal.symbol,
            signal.metadata.get("condition", "Unknown"),
            signal.confidence
        )

        # GUI 시그널 발송
        self.signal_generated.emit({
            "type": signal.type.value,
            "symbol": signal.symbol,
            "price": signal.price,
            "source": signal.source,
            "exchange": exchange_name,
            "combination": signal.metadata.get("combination", "")
        })
    
    async def _evaluate_exit_conditions(self) -> List[Signal]:
        """청산 조건 평가"""
        signals = []
        
        for exchange_name, positions in self.positions.items():
            market_data = self.market_data_cache.get(exchange_name)
            if not market_data:
                continue
            
            for position in positions:
                for condition in self.exit_conditions:
                    try:
                        if condition.is_active():
                            signal = condition.evaluate(market_data, position)
                            if signal:
                                signal.metadata["exchange"] = exchange_name
                                signal.metadata["position_id"] = position.symbol
                                signals.append(signal)
                                
                                # 신호 로그
                                trading_logger.log_signal(
                                    signal.type.value,
                                    signal.symbol,
                                    condition.get_name(),
                                    signal.confidence
                                )
                    
                    except Exception as e:
                        logger.error(f"청산 조건 평가 오류: {condition.get_name()} - {e}")
        
        return signals
    
    async def _execute_signals(self, entry_signals: List[Signal], exit_signals: List[Signal]) -> None:
        """신호 실행"""
        # 청산 신호 우선 처리
        for signal in exit_signals:
            await self._execute_exit_signal(signal)
        
        # 진입 신호 처리
        for signal in entry_signals:
            await self._execute_entry_signal(signal)
    
    async def _execute_entry_signal(self, signal: Signal) -> None:
        """진입 신호 실행"""
        try:
            exchange_name = signal.metadata.get("exchange")
            connector = self.api_connectors.get(exchange_name)
            
            if not connector:
                logger.error(f"거래소 커넥터를 찾을 수 없음: {exchange_name}")
                return
            
            # 포지션 크기 계산
            quantity = self._calculate_position_size(signal)
            
            # 주문 생성
            order = signal.to_order(quantity)
            
            # 주문 실행 (place_order는 동기 함수)
            perf_logger.start_timer(f"place_order_{exchange_name}")
            result = connector.place_order(order)
            perf_logger.end_timer(f"place_order_{exchange_name}")
            
            # OrderResponse는 status 속성을 가지고 있음
            if result.status == OrderStatus.FILLED:
                # 거래 로그
                trading_logger.log_entry(
                    signal.symbol,
                    signal.type.value,
                    quantity,
                    result.average_price or result.price,
                    signal.source
                )
                
                # 거래 실행 시그널 발송
                self.trade_executed.emit({
                    "type": "ENTRY",
                    "symbol": signal.symbol,
                    "side": signal.type.value,
                    "quantity": quantity,
                    "price": result.average_price or result.price,
                    "exchange": exchange_name
                })
                
                # 통계 업데이트
                self.trading_stats.update_stats(0, result.commission)
                
                logger.info(f"진입 주문 체결: {signal.symbol} {signal.type.value} {quantity}")
            
        except Exception as e:
            logger.error(f"진입 신호 실행 오류: {e}")
            trading_logger.log_error("ENTRY_EXECUTION", str(e))
    
    async def _execute_exit_signal(self, signal: Signal) -> None:
        """청산 신호 실행"""
        try:
            exchange_name = signal.metadata.get("exchange")
            connector = self.api_connectors.get(exchange_name)
            
            if not connector:
                logger.error(f"거래소 커넥터를 찾을 수 없음: {exchange_name}")
                return
            
            # 포지션 청산
            result = await connector.close_position(signal.symbol)
            
            # OrderResponse는 status 속성을 가지고 있음
            if result.status == OrderStatus.FILLED:
                # PnL 계산 (실제로는 포지션 정보에서 계산)
                pnl = 0.0  # 실제 구현에서는 포지션 정보를 통해 계산
                
                # 거래 로그
                trading_logger.log_exit(
                    signal.symbol,
                    signal.type.value,
                    result.filled_quantity,
                    result.average_price or result.price,
                    pnl,
                    signal.source
                )
                
                # 거래 실행 시그널 발송
                self.trade_executed.emit({
                    "type": "EXIT",
                    "symbol": signal.symbol,
                    "side": signal.type.value,
                    "quantity": result.filled_quantity,
                    "price": result.average_price or result.price,
                    "pnl": pnl,
                    "exchange": exchange_name
                })
                
                # 통계 업데이트
                self.trading_stats.update_stats(pnl, result.commission)
                
                logger.info(f"청산 주문 체결: {signal.symbol} PnL: {pnl}")
            
        except Exception as e:
            logger.error(f"청산 신호 실행 오류: {e}")
            trading_logger.log_error("EXIT_EXECUTION", str(e))
    
    def _calculate_position_size(self, signal: Signal) -> float:
        """포지션 크기 계산"""
        # BTCUSDT는 최소 0.001 BTC, 최소 주문금액 $100 필요
        # 현재 BTC 가격이 약 $112,000이므로 0.001 BTC = 약 $112

        # 바이낸스 최소 주문 수량 (BTCUSDT)
        min_quantity_btc = 0.001

        # 심볼에 따른 최소 수량 설정
        if "BTC" in signal.symbol:
            # BTC 페어는 최소 0.001 BTC 사용
            quantity = min_quantity_btc
            logger.info(f"BTC 페어 - 고정 수량 사용: {quantity} BTC (약 ${quantity * signal.price:,.2f})")
        else:
            # 다른 페어는 기존 계산 사용
            quantity = self.config.position_size / signal.price
            logger.info(f"계산된 수량: {quantity:.6f}")

        return quantity
    
    async def _update_positions(self) -> None:
        """포지션 업데이트"""
        for exchange_name, connector in self.api_connectors.items():
            try:
                # BinanceFuturesClient의 get_positions는 동기 메서드
                if hasattr(connector, 'get_positions'):
                    positions = connector.get_positions()  # await 제거
                else:
                    positions = []

                self.positions[exchange_name] = positions

                # 포지션 업데이트 시그널 발송
                if positions:
                    self.position_updated.emit({
                        "exchange": exchange_name,
                        "positions": [
                            {
                                "symbol": pos.symbol,
                                "side": pos.side.value if hasattr(pos.side, 'value') else pos.side,
                                "size": pos.size,
                                "entry_price": pos.entry_price,
                                "current_price": pos.current_price,
                                "pnl": pos.unrealized_pnl,
                                "pnl_percentage": pos.calculate_pnl_percentage() if hasattr(pos, 'calculate_pnl_percentage') else 0
                            }
                            for pos in positions
                        ]
                    })

            except Exception as e:
                logger.error(f"{exchange_name} 포지션 업데이트 오류: {e}")

    async def _update_account_info(self) -> None:
        """계좌 정보 업데이트"""
        for exchange_name, connector in self.api_connectors.items():
            try:
                # BinanceFuturesClient의 get_account_info는 동기 메서드
                if hasattr(connector, 'get_account_info'):
                    account_info = connector.get_account_info()  # await 제거
                    # 계좌 정보 처리 로직
                    if account_info:
                        logger.debug(f"{exchange_name} 계좌 잔고: {account_info.total_balance}")

            except Exception as e:
                logger.error(f"{exchange_name} 계좌 정보 업데이트 오류: {e}")
    
    def _update_system_status(self) -> None:
        """시스템 상태 업데이트"""
        total_positions = sum(len(positions) for positions in self.positions.values())
        
        self.system_status.update_status(
            is_trading_enabled=self.is_trading_enabled,
            active_positions=total_positions
        )
        
        # 상태 변경 시그널 발송
        self.status_changed.emit(self._get_status_dict())
    
    def _get_status_dict(self) -> Dict[str, Any]:
        """상태 딕셔너리 반환"""
        return {
            "is_running": self.system_status.is_running,
            "is_trading_enabled": self.system_status.is_trading_enabled,
            "connected_exchanges": self.system_status.connected_exchanges,
            "active_positions": self.system_status.active_positions,
            "total_trades": self.trading_stats.total_trades,
            "win_rate": self.trading_stats.win_rate,
            "total_pnl": self.trading_stats.total_pnl,
            "last_update": self.system_status.last_update
        }
    
    # 외부 인터페이스 메서드
    def enable_trading(self) -> None:
        """거래 활성화"""
        self.is_trading_enabled = True
        logger.info("거래 활성화")
    
    def disable_trading(self) -> None:
        """거래 비활성화"""
        self.is_trading_enabled = False
        logger.info("거래 비활성화")
    
    def add_entry_condition(self, condition) -> None:
        """진입 조건 추가"""
        self.entry_conditions.append(condition)
        logger.info(f"진입 조건 추가: {condition.get_name()}")
    
    def add_exit_condition(self, condition) -> None:
        """청산 조건 추가"""
        self.exit_conditions.append(condition)
        logger.info(f"청산 조건 추가: {condition.get_name()}")
    
    def set_risk_manager(self, risk_manager) -> None:
        """리스크 관리자 설정"""
        self.risk_manager = risk_manager
        logger.info("리스크 관리자 설정 완료")

    def set_time_control(self, time_config: Dict[str, Any]) -> None:
        """시간 제어 설정"""
        self.time_control = time_config
        logger.info(f"시간 제어 설정 완료: 24시간={time_config.get('full_time', False)}")

    def set_combination_mode(self, mode: str) -> None:
        """조건 조합 방식 설정 (AND/OR)"""
        if mode in ["AND", "OR"]:
            self.combination_mode = mode
            logger.info(f"조건 조합 방식 설정: {mode}")
        else:
            logger.warning(f"잘못된 조합 방식: {mode}, 기본값 OR 사용")
    
    def get_trading_stats(self) -> TradingStats:
        """거래 통계 반환"""
        return self.trading_stats
    
    def get_system_status(self) -> SystemStatus:
        """시스템 상태 반환"""
        return self.system_status
    
    def get_positions(self, exchange: Optional[str] = None) -> Dict[str, List[Position]]:
        """포지션 반환"""
        if exchange:
            return {exchange: self.positions.get(exchange, [])}
        return self.positions.copy()
    
    def get_market_data(self, exchange: Optional[str] = None) -> Dict[str, MarketData]:
        """시장 데이터 반환"""
        if exchange:
            return {exchange: self.market_data_cache.get(exchange)}
        return self.market_data_cache.copy()
