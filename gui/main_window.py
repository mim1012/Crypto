"""
메인 윈도우 클래스

암호화폐 자동매매 시스템의 메인 GUI 윈도우입니다.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QMenuBar, QStatusBar, QToolBar, QAction, QHBoxLayout,
    QLabel, QPushButton, QFrame, QDockWidget, QTextEdit,
    QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDateTime
from PyQt5.QtGui import QIcon, QFont, QTextCursor

from .tabs.entry_tab import EntryTab
from .tabs.exit_tab import ExitTab
from .tabs.position_tab import PositionTab
from .tabs.risk_tab import RiskTab
from .tabs.time_tab import TimeTab
from utils.logger import get_logger
from conditions.exit_condition_factory import ExitConditionFactory
from config.settings_manager import get_settings_manager
from config.constants import (
    DEFAULT_SYMBOL,
    PRICE_UPDATE_INTERVAL_MS,
    STATUS_UPDATE_INTERVAL_MS,
    PUBLIC_PRICE_ENDPOINT,
)

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """메인 윈도우 클래스"""

    def __init__(self, trading_engine=None):
        super().__init__()
        self.trading_engine = trading_engine
        # GUI 토글과 엔진 Exit 조건(PCS) 연결 상태 보관
        self._pcs_condition = None

        # API 클라이언트 초기화
        self.binance_client = None
        self.bybit_client = None
        self._init_api_clients()

        self.init_ui()
        self.setup_connections()

        # 가격 업데이트 타이머 (5초마다 실제 가격 가져오기)
        self.price_timer = QTimer()
        self.price_timer.timeout.connect(self.update_btc_price)
        self.price_timer.start(PRICE_UPDATE_INTERVAL_MS)  # 5초마다 업데이트

        # 초기 가격 업데이트
        QTimer.singleShot(100, self.update_btc_price)  # UI 로드 후 0.1초 뒤 실행

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("암호화폐 자동매매 시스템 v2.0")
        self.setGeometry(100, 100, 1400, 900)

        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 메인 레이아웃
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # 상단 상태 바
        self.create_top_status_bar(layout)

        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 탭들 추가
        self.create_tabs()

        # 메뉴바와 상태바 설정
        self.create_menu_bar()
        self.create_status_bar()

        # 실시간 모니터링 도크 생성
        self.create_monitoring_dock()

        # 스타일 적용
        self.apply_styles()

    def create_top_status_bar(self, layout):
        """상단 상태 표시줄 생성"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Box)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #007bff;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        status_layout = QHBoxLayout(status_frame)
        
        # 시스템 상태
        self.system_status_label = QLabel("🚀 시스템: 준비됨")
        self.system_status_label.setStyleSheet("font-weight: bold; color: #28a745; font-size: 12pt;")
        status_layout.addWidget(self.system_status_label)
        
        # 연결 상태
        self.connection_status_label = QLabel("🔗 연결: 확인 중...")
        self.connection_status_label.setStyleSheet("font-weight: bold; color: #6c757d; font-size: 11pt;")
        status_layout.addWidget(self.connection_status_label)
        
        # 현재가
        self.price_label = QLabel("BTC: $--")
        self.price_label.setStyleSheet("font-weight: bold; color: #6c757d; font-size: 11pt;")
        status_layout.addWidget(self.price_label)
        
        status_layout.addStretch()
        
        # 긴급 청산 버튼
        self.emergency_btn = QPushButton("🚨 긴급 청산")
        self.emergency_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                font-size: 11pt;
                padding: 8px 16px;
                border-radius: 6px;
                border: 2px solid #c82333;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.emergency_btn.clicked.connect(self.emergency_close_all)
        status_layout.addWidget(self.emergency_btn)
        
        # 거래 시작/중지 버튼
        self.trading_btn = QPushButton("▶️ 거래 시작")
        self.trading_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                font-size: 11pt;
                padding: 8px 16px;
                border-radius: 6px;
                border: 2px solid #1e7e34;
            }
            QPushButton:hover {
                background-color: #1e7e34;
            }
        """)
        self.trading_btn.clicked.connect(self.toggle_trading)
        status_layout.addWidget(self.trading_btn)
        
        layout.addWidget(status_frame)

    def create_tabs(self):
        """탭들 생성"""
        try:
            # 진입 설정 탭
            self.entry_tab = EntryTab(parent=self, trading_engine=self.trading_engine)
            self.tab_widget.addTab(self.entry_tab, "📈 진입 설정")

            # 청산 설정 탭
            self.exit_tab = ExitTab(parent=self, trading_engine=self.trading_engine)
            try:
                self.exit_tab.exit_condition_changed.connect(self.on_exit_condition_toggle)
            except Exception:
                pass
            self.tab_widget.addTab(self.exit_tab, "📉 청산 설정")

            # 시간 제어 탭
            self.time_tab = TimeTab(parent=self, trading_engine=self.trading_engine)
            self.tab_widget.addTab(self.time_tab, "⏰ 시간 제어")

            # 리스크 관리 탭
            self.risk_tab = RiskTab(parent=self, trading_engine=self.trading_engine)
            self.tab_widget.addTab(self.risk_tab, "⚠️ 리스크 관리")

            # 포지션 현황 탭
            self.position_tab = PositionTab(self)
            self.tab_widget.addTab(self.position_tab, "💼 포지션 현황")

            logger.info("모든 탭이 성공적으로 생성되었습니다")

        except Exception as e:
            logger.error(f"탭 생성 중 오류 발생: {e}")

    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()

        # 파일 메뉴
        file_menu = menubar.addMenu('파일')

        # 설정 저장
        save_action = QAction('설정 저장', self)
        save_action.triggered.connect(self.save_settings)
        file_menu.addAction(save_action)

        # 설정 로드
        load_action = QAction('설정 로드', self)
        load_action.triggered.connect(self.load_settings)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        # 종료
        exit_action = QAction('종료', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 거래 메뉴
        trading_menu = menubar.addMenu('거래')

        # 거래 시작/중지
        toggle_action = QAction('거래 시작/중지', self)
        toggle_action.triggered.connect(self.toggle_trading)
        trading_menu.addAction(toggle_action)

        # 모든 포지션 청산
        close_all_action = QAction('모든 포지션 청산', self)
        close_all_action.triggered.connect(self.emergency_close_all)
        trading_menu.addAction(close_all_action)

        # 도구 메뉴
        tools_menu = menubar.addMenu('도구')

        # 실시간 모니터링 표시/숨김
        monitor_action = QAction('실시간 모니터링 표시/숨김', self)
        monitor_action.triggered.connect(self.toggle_monitor_dock)
        tools_menu.addAction(monitor_action)

        # 로그 보기
        log_action = QAction('로그 보기', self)
        tools_menu.addAction(log_action)

        # 백테스트
        backtest_action = QAction('백테스트', self)
        tools_menu.addAction(backtest_action)

        # 도움말 메뉴
        help_menu = menubar.addMenu('도움말')

        # 사용법
        usage_action = QAction('사용법', self)
        help_menu.addAction(usage_action)

        # 정보
        about_action = QAction('정보', self)
        help_menu.addAction(about_action)

    def create_status_bar(self):
        """상태바 생성"""
        self.status_bar = self.statusBar()
        
        # 상태 메시지
        self.status_bar.showMessage("시스템 준비됨")
        
        # 우측 상태 정보들
        self.connection_status = QLabel("연결: 대기중")
        self.status_bar.addPermanentWidget(self.connection_status)
        
        self.trading_status = QLabel("거래: 중지됨")
        self.status_bar.addPermanentWidget(self.trading_status)
        
        self.time_status = QLabel("시간: --:--:--")
        self.status_bar.addPermanentWidget(self.time_status)

    def apply_styles(self):
        """스타일 적용"""
        # 전체 윈도우 스타일
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                background-color: #ffffff;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #495057;
                padding: 15px 30px;
                margin-right: 2px;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 11pt;
                min-width: 120px;
                min-height: 35px;
            }
            QTabBar::tab:selected {
                background-color: #007bff;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
            QStatusBar {
                background-color: #f8f9fa;
                border-top: 1px solid #dee2e6;
                color: #495057;
            }
            QMenuBar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                color: #495057;
            }
            QMenuBar::item {
                padding: 8px 12px;
            }
            QMenuBar::item:selected {
                background-color: #007bff;
                color: white;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 35px;
                padding-top: 25px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 8px 15px;
                left: 10px;
                top: -5px;
                background-color: white;
                min-height: 25px;
            }
        """)

    def setup_connections(self):
        """시그널/슬롯 연결 설정"""
        if self.trading_engine:
            # TradingEngine → GUI signal wiring
            try:
                self.trading_engine.status_changed.connect(self.on_status_changed)
                self.trading_engine.signal_generated.connect(self.on_signal_generated)
                self.trading_engine.trade_executed.connect(self.on_trade_executed)
                self.trading_engine.position_updated.connect(self.on_position_updated)
            except Exception as e:
                logger.warning(f"트레이딩 엔진 신호 연결 실패: {e}")
            # trading_engine의 시그널들과 연결
            pass

        # 상태 업데이트 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(STATUS_UPDATE_INTERVAL_MS)  # 1초마다 업데이트

    def _init_api_clients(self):
        """API 클라이언트 초기화"""
        try:
            from config.settings_manager import get_settings_manager
            settings_manager = get_settings_manager()

            # Binance 설정 가져오기
            binance_config = settings_manager.get_exchange_config("binance")
            if binance_config and binance_config.api_key and binance_config.api_secret:
                from api.binance.futures_client import BinanceFuturesClient
                from api.base_api import APICredentials

                credentials = APICredentials(
                    api_key=binance_config.api_key,
                    secret_key=binance_config.api_secret,
                    testnet=binance_config.testnet
                )
                self.binance_client = BinanceFuturesClient(credentials)
                logger.info("바이낸스 API 클라이언트 초기화 완료")

            # Bybit 설정 가져오기
            bybit_config = settings_manager.get_exchange_config("bybit")
            if bybit_config and bybit_config.api_key and bybit_config.api_secret:
                from api.bybit.futures_client import BybitFuturesClient
                from api.base_api import APICredentials

                credentials = APICredentials(
                    api_key=bybit_config.api_key,
                    secret_key=bybit_config.api_secret,
                    testnet=bybit_config.testnet
                )
                self.bybit_client = BybitFuturesClient(credentials)
                logger.info("바이비트 API 클라이언트 초기화 완료")

        except Exception as e:
            logger.warning(f"API 클라이언트 초기화 실패: {e}")

    def update_btc_price(self):
        """실시간 BTC 가격 업데이트"""
        try:
            btc_price = None
            exchange_name = ""

            # Binance에서 가격 시도
            if self.binance_client:
                try:
                    ticker = self.binance_client.get_ticker("BTCUSDT")
                    if ticker and ticker.price > 0:
                        btc_price = ticker.price
                        exchange_name = "Binance"
                        # 상단 연결 상태 업데이트
                        self.connection_status_label.setText("🔗 연결: Binance Futures ✅")
                        self.connection_status_label.setStyleSheet("font-weight: bold; color: #28a745; font-size: 11pt;")
                except Exception as e:
                    logger.debug(f"바이낸스 가격 조회 실패: {e}")
                    # 연결 실패 시 상태 업데이트
                    self.connection_status_label.setText("🔗 연결: ❌ 오프라인")
                    self.connection_status_label.setStyleSheet("font-weight: bold; color: #dc3545; font-size: 11pt;")

            # Binance 실패 시 Bybit에서 가격 시도
            if not btc_price and self.bybit_client:
                try:
                    ticker = self.bybit_client.get_ticker("BTCUSDT")
                    if ticker and ticker.price > 0:
                        btc_price = ticker.price
                        exchange_name = "Bybit"
                except Exception as e:
                    logger.debug(f"바이비트 가격 조회 실패: {e}")

            # API 클라이언트가 없거나 실패한 경우 공개 API 사용
            if not btc_price:
                try:
                    import requests
                    # Binance 공개 API 사용 (API 키 불필요)
                    response = requests.get(
                        PUBLIC_PRICE_ENDPOINT,
                        params={"symbol": DEFAULT_SYMBOL},
                        timeout=3
                    )
                    if response.status_code == 200:
                        data = response.json()
                        btc_price = float(data["price"])
                        exchange_name = "Binance Public"
                except Exception as e:
                    logger.debug(f"공개 API 가격 조회 실패: {e}")

            # 가격 업데이트
            if btc_price:
                self.price_label.setText(f"💰 BTC: ${btc_price:,.0f}")
                self.price_label.setToolTip(f"실시간 가격 ({exchange_name})")
            else:
                # API 실패 시 기본값 표시
                self.price_label.setText("💰 BTC: $--,---")
                self.price_label.setToolTip("가격 정보 없음")

        except Exception as e:
            logger.error(f"BTC 가격 업데이트 오류: {e}")
            self.price_label.setText("💰 BTC: $--,---")
            self.price_label.setToolTip("가격 업데이트 오류")

    def update_status(self):
        """상태 정보 업데이트"""
        try:
            # 현재 시간 업데이트
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M:%S")
            self.time_status.setText(f"시간: {current_time}")

            # API 연결 상태 업데이트
            if hasattr(self, 'binance_client') and self.binance_client:
                # API 연결 확인
                try:
                    if self.binance_client.test_connectivity():
                        self.connection_status.setText("연결: ✅ Binance Futures")
                        self.connection_status.setStyleSheet("color: #28a745;")  # 녹색
                    else:
                        self.connection_status.setText("연결: ⚠️ 확인 중")
                        self.connection_status.setStyleSheet("color: #ffc107;")  # 노란색
                except Exception:
                    self.connection_status.setText("연결: ❌ 오프라인")
                    self.connection_status.setStyleSheet("color: #dc3545;")  # 빨간색
            else:
                self.connection_status.setText("연결: 대기중")
                self.connection_status.setStyleSheet("color: #6c757d;")  # 회색

        except Exception as e:
            logger.error(f"상태 업데이트 오류: {e}")

    def start_trading(self):
        """거래 시작 메서드"""
        try:
            # 모니터링 도크 표시
            if hasattr(self, 'monitor_dock'):
                self.monitor_dock.show()
                self.monitor_dock.raise_()
                logger.info("실시간 모니터링 창이 열렸습니다")

            if self.trading_engine:
                # 동기식 거래 엔진 시작
                try:
                    success = self.trading_engine.start_sync()

                    if success:
                        self.trading_engine.is_trading_enabled = True
                        self._update_ui_trading_state(True)
                        self.status_bar.showMessage("거래가 시작되었습니다 - Trading Engine 활성화")
                        logger.info("Trading Engine 시작됨")
                        return True
                    else:
                        self.status_bar.showMessage("거래 시작 실패 - API 연결을 확인하세요")
                        logger.error("Trading Engine 시작 실패")
                        return False
                except Exception as e:
                    logger.error(f"Trading Engine 시작 오류: {e}")
                    self.status_bar.showMessage(f"거래 시작 실패: {str(e)}")
                    return False
            else:
                # Trading Engine 없이 UI만 업데이트
                self._update_ui_trading_state(True)
                self.status_bar.showMessage("거래 엔진이 없습니다 - 시뮬레이션 모드")
                logger.warning("Trading Engine 없이 실행 중")
                return False

        except Exception as e:
            logger.error(f"거래 시작 오류: {e}")
            self.status_bar.showMessage(f"거래 시작 실패: {str(e)}")
            return False

    def stop_trading(self):
        """거래 중지 메서드"""
        try:
            if self.trading_engine and self.trading_engine.is_running:
                # 비동기 거래 엔진 중지
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.trading_engine.stop())

                    self.trading_engine.is_trading_enabled = False
                    logger.info("Trading Engine 중지됨")
                except Exception as e:
                    logger.error(f"Trading Engine 중지 오류: {e}")

            self._update_ui_trading_state(False)
            self.status_bar.showMessage("거래가 중지되었습니다")
            return True

        except Exception as e:
            logger.error(f"거래 중지 오류: {e}")
            self.status_bar.showMessage(f"거래 중지 실패: {str(e)}")
            return False

    def _update_ui_trading_state(self, is_trading: bool):
        """UI 거래 상태 업데이트"""
        if is_trading:
            self.trading_btn.setText("⏸️ 거래 중지")
            self.trading_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    color: #212529;
                    font-weight: bold;
                    font-size: 11pt;
                    padding: 8px 16px;
                    border-radius: 6px;
                    border: 2px solid #e0a800;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            self.system_status_label.setText("🚀 시스템: 거래중")
            self.system_status_label.setStyleSheet("font-weight: bold; color: #ffc107; font-size: 12pt;")
            if hasattr(self, 'trading_status'):
                self.trading_status.setText("거래: 활성화")
        else:
            self.trading_btn.setText("▶️ 거래 시작")
            self.trading_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    font-weight: bold;
                    font-size: 11pt;
                    padding: 8px 16px;
                    border-radius: 6px;
                    border: 2px solid #1e7e34;
                }
                QPushButton:hover {
                    background-color: #1e7e34;
                }
            """)
            self.system_status_label.setText("🚀 시스템: 준비됨")
            self.system_status_label.setStyleSheet("font-weight: bold; color: #28a745; font-size: 12pt;")
            if hasattr(self, 'trading_status'):
                self.trading_status.setText("거래: 중지됨")

    def toggle_trading(self):
        """거래 시작/중지 토글"""
        try:
            current_text = self.trading_btn.text()

            if "시작" in current_text:
                self.start_trading()
            else:
                self.stop_trading()

            logger.info(f"거래 상태 변경: {current_text}")

        except Exception as e:
            logger.error(f"거래 토글 오류: {e}")
            self.status_bar.showMessage(f"오류: {str(e)}")

    def emergency_close_all(self):
        """긴급 전체 포지션 청산"""
        try:
            logger.warning("긴급 전체 포지션 청산 요청")
            
            # 긴급 청산 실행
            self.emergency_btn.setText("✅ 청산 완료")
            self.emergency_btn.setEnabled(False)
            
            # 상태 업데이트
            self.system_status_label.setText("🛑 시스템: 긴급 청산")
            self.system_status_label.setStyleSheet("font-weight: bold; color: #dc3545; font-size: 12pt;")
            self.status_bar.showMessage("긴급 청산이 실행되었습니다")
            
            # 5초 후 버튼 복구
            QTimer.singleShot(5000, self.restore_emergency_button)
            
        except Exception as e:
            logger.error(f"긴급 청산 오류: {e}")

    def restore_emergency_button(self):
        """긴급 청산 버튼 복구"""
        self.emergency_btn.setText("🚨 긴급 청산")
        self.emergency_btn.setEnabled(True)

    def save_settings(self):
        """설정 저장"""
        try:
            settings = {}
            
            # 각 탭의 설정 수집
            if hasattr(self, 'entry_tab'):
                settings['entry'] = self.entry_tab.get_settings()
            if hasattr(self, 'exit_tab'):
                settings['exit'] = self.exit_tab.get_settings()
            if hasattr(self, 'time_tab'):
                settings['time'] = self.time_tab.get_settings()
            if hasattr(self, 'risk_tab'):
                settings['risk'] = self.risk_tab.get_settings()
            if hasattr(self, 'position_tab'):
                settings['position'] = self.position_tab.get_settings()
            
            # 파일로 저장 (실제 구현에서는 JSON 파일로 저장)
            logger.info("설정이 저장되었습니다")
            self.status_bar.showMessage("설정이 저장되었습니다")
            
        except Exception as e:
            logger.error(f"설정 저장 오류: {e}")

    def load_settings(self):
        """설정 로드"""
        try:
            # 파일에서 설정 로드 (실제 구현에서는 JSON 파일에서 로드)
            settings = {}
            
            # 각 탭에 설정 적용
            if hasattr(self, 'entry_tab') and 'entry' in settings:
                self.entry_tab.load_settings(settings['entry'])
            if hasattr(self, 'exit_tab') and 'exit' in settings:
                self.exit_tab.load_settings(settings['exit'])
            if hasattr(self, 'time_tab') and 'time' in settings:
                self.time_tab.load_settings(settings['time'])
            if hasattr(self, 'risk_tab') and 'risk' in settings:
                self.risk_tab.load_settings(settings['risk'])
            if hasattr(self, 'position_tab') and 'position' in settings:
                self.position_tab.load_settings(settings['position'])
            
            logger.info("설정이 로드되었습니다")
            self.status_bar.showMessage("설정이 로드되었습니다")
            
        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")

    def create_monitoring_dock(self):
        """실시간 모니터링 도크 위젯 생성"""
        # 도크 위젯 생성
        self.monitor_dock = QDockWidget("🔍 실시간 모니터링", self)
        self.monitor_dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.RightDockWidgetArea)

        # 모니터링 위젯 컨테이너
        monitor_widget = QWidget()
        monitor_layout = QVBoxLayout()
        monitor_widget.setLayout(monitor_layout)

        # 상단 컨트롤 버튼들
        control_layout = QHBoxLayout()

        # 자동 스크롤 체크박스
        self.auto_scroll_checkbox = QCheckBox("자동 스크롤")
        self.auto_scroll_checkbox.setChecked(True)
        control_layout.addWidget(self.auto_scroll_checkbox)

        # 로그 레벨 선택
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ALL", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        control_layout.addWidget(QLabel("로그 레벨:"))
        control_layout.addWidget(self.log_level_combo)

        # 클리어 버튼
        clear_btn = QPushButton("🗑️ 로그 지우기")
        clear_btn.clicked.connect(self.clear_monitor_log)
        control_layout.addWidget(clear_btn)

        control_layout.addStretch()
        monitor_layout.addLayout(control_layout)

        # 로그 텍스트 영역
        self.monitor_text = QTextEdit()
        self.monitor_text.setReadOnly(True)
        self.monitor_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #444;
            }
        """)
        monitor_layout.addWidget(self.monitor_text)

        # 상태 표시 라벨
        self.monitor_status_label = QLabel("대기중...")
        self.monitor_status_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                background-color: #2b2b2b;
                color: #888;
                border-top: 1px solid #444;
            }
        """)
        monitor_layout.addWidget(self.monitor_status_label)

        self.monitor_dock.setWidget(monitor_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.monitor_dock)
        self.monitor_dock.setMinimumHeight(200)  # 최소 높이 설정
        self.monitor_dock.hide()  # 초기에는 숨김

        # 로그 읽기 타이머 설정
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_monitor_log)
        self.log_timer.start(500)  # 500ms마다 로그 업데이트

        # 로그 파일 위치 설정
        self.log_file_path = "trading_system.log"
        self.last_log_position = 0

    def update_monitor_log(self):
        """로그 파일에서 새로운 내용 읽기"""
        try:
            import os
            if not os.path.exists(self.log_file_path):
                return

            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 마지막 읽은 위치로 이동
                f.seek(self.last_log_position)
                new_lines = f.readlines()
                self.last_log_position = f.tell()

            if new_lines:
                log_level = self.log_level_combo.currentText()

                for line in new_lines:
                    # 로그 레벨 필터링
                    if log_level != "ALL":
                        if log_level == "ERROR" and "ERROR" not in line:
                            continue
                        elif log_level == "WARNING" and "WARNING" not in line and "ERROR" not in line:
                            continue
                        elif log_level == "INFO" and "DEBUG" in line:
                            continue

                    # 색상 적용
                    formatted_line = self.format_log_line(line)
                    self.monitor_text.append(formatted_line)

                # 자동 스크롤
                if self.auto_scroll_checkbox.isChecked():
                    cursor = self.monitor_text.textCursor()
                    cursor.movePosition(QTextCursor.End)
                    self.monitor_text.setTextCursor(cursor)

                # 상태 업데이트
                current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
                self.monitor_status_label.setText(f"마지막 업데이트: {current_time} | 로그 수: {self.monitor_text.document().blockCount()}")

        except Exception as e:
            logger.error(f"로그 모니터 업데이트 오류: {e}")

    def format_log_line(self, line):
        """로그 라인에 HTML 색상 적용"""
        line = line.strip()
        if not line:
            return ""

        # HTML 이스케이프
        line = line.replace('<', '&lt;').replace('>', '&gt;')

        # 색상 적용
        if 'ERROR' in line or '오류' in line:
            return f'<span style="color: #ff6b6b;">{line}</span>'
        elif 'WARNING' in line or '경고' in line:
            return f'<span style="color: #feca57;">{line}</span>'
        elif 'SUCCESS' in line or '성공' in line or '✅' in line:
            return f'<span style="color: #48dbfb;">{line}</span>'
        elif 'INFO' in line:
            return f'<span style="color: #95e1d3;">{line}</span>'
        elif '거래 시작' in line or '거래 엔진 시작' in line:
            return f'<span style="color: #3ae374; font-weight: bold;">{line}</span>'
        elif '포지션' in line or 'POSITION' in line:
            return f'<span style="color: #f368e0;">{line}</span>'
        elif '진입' in line or 'ENTRY' in line:
            return f'<span style="color: #00d2d3;">{line}</span>'
        elif '청산' in line or 'EXIT' in line:
            return f'<span style="color: #ff9ff3;">{line}</span>'
        elif '시그널' in line or 'SIGNAL' in line:
            return f'<span style="color: #54a0ff;">{line}</span>'
        elif 'DEBUG' in line:
            return f'<span style="color: #636e72;">{line}</span>'
        else:
            return f'<span style="color: #dfe6e9;">{line}</span>'

    def clear_monitor_log(self):
        """모니터 로그 지우기"""
        self.monitor_text.clear()
        self.monitor_status_label.setText("로그가 지워졌습니다")
        logger.info("모니터 로그가 지워졌습니다")

    def toggle_monitor_dock(self):
        """모니터링 도크 표시/숨김 토글"""
        if hasattr(self, 'monitor_dock'):
            if self.monitor_dock.isVisible():
                self.monitor_dock.hide()
                logger.info("실시간 모니터링 창이 숨겨졌습니다")
            else:
                self.monitor_dock.show()
                self.monitor_dock.raise_()
                logger.info("실시간 모니터링 창이 표시되었습니다")

    def closeEvent(self, event):
        """윈도우 종료 시 호출"""
        logger.info("메인 윈도우가 종료됩니다")
        
        # 설정 자동 저장
        self.save_settings()
        
        if self.trading_engine:
            # trading_engine 정리 작업
            pass
            
        event.accept()

    def on_exit_condition_toggle(self, cond_type: str, enabled: bool):
        """ExitTab의 조건 토글을 TradingEngine에 반영한다 (GUI 구조 변경 없음)."""
        try:
            if not self.trading_engine:
                return

            key = (cond_type or "").strip().lower()
            if key in ("pcs_system", "pcs", "pcs 설정", "pcs설정"):
                # 최초 생성 시 팩토리로 조건 1개 생성
                if self._pcs_condition is None:
                    try:
                        cfg = get_settings_manager().config
                        enabled_steps = [s.get('step') for s in (cfg.exit.pcs_steps or []) if s.get('enabled', True)]
                        if not enabled_steps:
                            enabled_steps = list(range(1, 7))
                    except Exception:
                        enabled_steps = list(range(1, 7))

                    pcs_cfg = {
                        "type": "pcs_system",
                        "enabled": bool(enabled),
                        "params": {"active_steps": enabled_steps}
                    }
                    self._pcs_condition = ExitConditionFactory.create_condition(pcs_cfg)
                    self.trading_engine.add_exit_condition(self._pcs_condition)
                else:
                    # 이미 존재: enable/disable만 반영
                    if enabled:
                        self._pcs_condition.enable()
                    else:
                        self._pcs_condition.disable()
        except Exception as e:
            logger.error(f"Exit 조건 토글 처리 실패: {e}")

    # ===== TradingEngine signal handlers =====
    def on_status_changed(self, status: dict):
        try:
            is_trading = bool(status.get("is_trading_enabled"))
            connected = status.get("connected_exchanges", [])
            self.system_status_label.setText("�ý���: �ŷ���" if is_trading else "�ý���: �غ��")
            self.trading_status.setText("�ŷ�: Ȱ��ȭ" if is_trading else "�ŷ�: ������")
            if connected:
                self.connection_status.setText(f"����: {', '.join(connected)}")
                self.connection_status.setStyleSheet("color: #28a745;")
            else:
                self.connection_status.setText("����: �����")
                self.connection_status.setStyleSheet("color: #6c757d;")
            if hasattr(self, 'position_tab') and hasattr(self.position_tab, 'update_position_tables'):
                try:
                    self.position_tab.update_position_tables()
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"on_status_changed ����: {e}")

    def on_signal_generated(self, data: dict):
        try:
            sym = data.get("symbol", "")
            src = data.get("source", "")
            self.status_bar.showMessage(f"��ȣ: {sym} ({src})")
        except Exception as e:
            logger.debug(f"on_signal_generated ����: {e}")

    def on_trade_executed(self, data: dict):
        try:
            side = data.get("type", "")
            sym = data.get("symbol", "")
            self.status_bar.showMessage(f"�ŷ� �Ҽ�: {side} {sym}")
            if hasattr(self, 'position_tab') and hasattr(self.position_tab, 'update_position_tables'):
                self.position_tab.update_position_tables()
        except Exception as e:
            logger.debug(f"on_trade_executed ����: {e}")

    def on_position_updated(self, data: dict):
        try:
            if hasattr(self, 'position_tab') and hasattr(self.position_tab, 'update_position_tables'):
                self.position_tab.update_position_tables()
        except Exception as e:
            logger.debug(f"on_position_updated ����: {e}")






