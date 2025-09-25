"""
진입 설정 탭 모듈 - 완전 복원 버전

이 모듈은 거래 진입 조건 설정 UI를 구현합니다.
원본 GUI의 모든 기능을 모듈화된 구조로 완전 복원했습니다.
"""

from typing import Dict, Any, List
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QCheckBox, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QFrame, QTabWidget, QWidget,
    QScrollArea, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from gui.base_tab import BaseTab
from gui.dialogs.api_test_dialog import APITestDialog
from utils.logger import get_logger
from config.settings_manager import get_settings_manager

logger = get_logger(__name__)


class EntryTab(BaseTab):
    """진입 설정 탭 - 완전 복원"""
    
    # 진입 조건 관련 시그널
    condition_changed = pyqtSignal(str, bool)
    entry_signal_detected = pyqtSignal(str, dict)
    
    def __init__(self, parent=None, trading_engine=None):
        super().__init__("진입 설정", parent)

        self.trading_engine = trading_engine
        # 진입 조건 상태
        self.entry_conditions = {}
        self.condition_widgets = {}
        self.exchange_tabs = {}

        # 실시간 업데이트 타이머
        from PyQt5.QtCore import QTimer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_monitoring_data)
        self.update_timer.start(2000)  # 2초마다 업데이트
        
        # 실시간 모니터링 데이터 (실제 API에서 업데이트됨)
        self.market_data = {
            'current_price': 0,
            'ma_value': 0,
            'pc_upper': 0,
            'pc_lower': 0,
            'signal_count': 0
        }
        self.signal_status = {}
    
    def init_ui(self) -> None:
        """UI 초기화 - 원본 GUI 완전 복원"""
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 스크롤 영역 생성
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        
        # 1. 진입 신호 모니터링
        self.create_entry_monitoring(scroll_layout)
        
        # 2. 다중 거래소 설정 (듀얼 시스템)
        self.create_exchange_settings(scroll_layout)
        
        # 3. 조건 조합 방식
        self.create_condition_combination(scroll_layout)
        
        # 구분선
        self.add_entry_separator(scroll_layout)
        
        # 4. 이동평균선 조건
        self.create_moving_average_condition(scroll_layout)
        
        # 구분선
        self.add_entry_separator(scroll_layout)
        
        # 5. Price Channel 조건
        self.create_price_channel_condition(scroll_layout)
        
        # 구분선
        self.add_entry_separator(scroll_layout)
        
        # 6. 호가 감시 조건
        self.create_orderbook_watch_condition(scroll_layout)
        
        # 구분선
        self.add_entry_separator(scroll_layout)
        
        # 7. 캔들 상태 조건
        self.create_candle_state_condition(scroll_layout)
        
        # 구분선
        self.add_entry_separator(scroll_layout)
        
        # 8. 틱 기반 추가 진입
        self.create_tick_based_condition(scroll_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
        
        # 실시간 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_monitoring_data)
        self.update_timer.start(1000)  # 1초마다 업데이트

        # 시그널 연결
        self.connect_condition_signals()

        # 설정값 로드 (API 키 포함)
        self.load_settings({})
    
    def create_entry_monitoring(self, layout):
        """진입 신호 모니터링"""
        group = QGroupBox("📊 진입 신호 모니터링")
        group_layout = QVBoxLayout(group)
        
        # 현재가 정보
        price_layout = QHBoxLayout()
        self.current_price_label = QLabel("현재가: 50,185")
        self.ma_value_label = QLabel("이평선: 49,026")
        self.signal_count_label = QLabel("신호 발생: 0개")
        
        price_layout.addWidget(self.current_price_label)
        price_layout.addStretch()
        price_layout.addWidget(self.ma_value_label)
        price_layout.addStretch()
        price_layout.addWidget(self.signal_count_label)
        group_layout.addWidget(self.create_frame_layout(price_layout))
        
        # PC 범위 정보
        pc_layout = QHBoxLayout()
        self.pc_range_label = QLabel("PC 범위: 49,432 ~ 50,937")
        pc_layout.addWidget(self.pc_range_label)
        group_layout.addWidget(self.create_frame_layout(pc_layout))
        
        # 조건별 실시간 상태
        conditions_frame = QFrame()
        conditions_frame.setFrameStyle(QFrame.Box)
        conditions_frame.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6;")
        conditions_layout = QVBoxLayout(conditions_frame)
        
        # 각 조건별 상태 라벨들
        self.condition_status_labels = {}
        conditions = [
            ("🎯 조건별 실시간 상태", ""),
            ("📊 이동평균선: 매수 조건 만족", "✅"),
            ("📈 Price Channel: 조건 대기중", "⏳"),
            ("🔔 호가 감지: 비활성", "⏸"),
            ("🕯 캔들 상태: 비활성", "⏸"),
            ("📈 틱 기반: 비활성", "⏸")
        ]
        
        for i, (condition, status) in enumerate(conditions):
            cond_layout = QHBoxLayout()
            condition_label = QLabel(condition)
            status_label = QLabel(status) if status else QLabel("")
            
            cond_layout.addWidget(condition_label)
            cond_layout.addStretch()
            cond_layout.addWidget(status_label)
            conditions_layout.addLayout(cond_layout)
            
            if i > 0:  # 첫 번째는 제목이므로 제외
                self.condition_status_labels[condition.split(':')[0].strip()] = (condition_label, status_label)
            
        group_layout.addWidget(conditions_frame)
        layout.addWidget(group)
        
    def create_exchange_settings(self, layout):
        """다중 거래소 설정"""
        group = QGroupBox("🏢 다중 거래소 설정")
        group_layout = QVBoxLayout(group)
        
        # 듀얼 거래소 선택 (바이낸스 + 바이비트)
        exchange_selection_layout = QHBoxLayout()
        exchange_selection_layout.addWidget(QLabel("🏢 듀얼 거래소 시스템:"))
        
        self.binance_check = QCheckBox("🟡 바이낸스 선물")
        self.binance_check.setChecked(True)
        self.binance_check.setStyleSheet("color: #f0b90b; font-weight: bold; font-size: 11pt;")
        exchange_selection_layout.addWidget(self.binance_check)
        
        self.bybit_check = QCheckBox("🟠 바이비트 선물")
        self.bybit_check.setChecked(True)
        self.bybit_check.setStyleSheet("color: #f7931a; font-weight: bold; font-size: 11pt;")
        exchange_selection_layout.addWidget(self.bybit_check)
        
        # 동시 거래 모드
        self.dual_mode_check = QCheckBox("⚡ 동시 거래 모드")
        self.dual_mode_check.setChecked(True)
        self.dual_mode_check.setStyleSheet("color: #28a745; font-weight: bold; font-size: 11pt;")
        exchange_selection_layout.addWidget(self.dual_mode_check)
        
        exchange_selection_layout.addStretch()
        group_layout.addLayout(exchange_selection_layout)
        
        # 거래소별 설정 탭 (바이낸스 + 바이비트만)
        self.exchange_tab_widget = QTabWidget()
        
        # 바이낸스 설정 탭
        binance_tab = self.create_binance_settings_tab()
        self.exchange_tab_widget.addTab(binance_tab, "🟡 바이낸스 선물")
        
        # 바이비트 설정 탭
        bybit_tab = self.create_bybit_settings_tab()
        self.exchange_tab_widget.addTab(bybit_tab, "🟠 바이비트 선물")
        
        group_layout.addWidget(self.exchange_tab_widget)
        
        # 듀얼 거래소 통합 상태
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Box)
        status_frame.setStyleSheet("background-color: #e8f5e8; border: 2px solid #28a745;")
        status_layout = QHBoxLayout(status_frame)
        
        self.binance_status_label = QLabel("🟡 바이낸스: ✅ 연결됨 (45ms)")
        self.bybit_status_label = QLabel("🟠 바이비트: ✅ 연결됨 (38ms)")
        self.dual_status_label = QLabel("⚡ 동시 거래: 활성화")
        
        status_layout.addWidget(QLabel("🚀 듀얼 거래소 상태:"))
        status_layout.addWidget(self.binance_status_label)
        status_layout.addWidget(self.bybit_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.dual_status_label)
        
        group_layout.addWidget(status_frame)
        layout.addWidget(group)
        
    def create_binance_settings_tab(self):
        """바이낸스 설정 탭"""
        tab = QWidget()
        layout = QGridLayout(tab)
        
        # 거래 심볼
        layout.addWidget(QLabel("거래 심볼:"), 0, 0)
        self.binance_symbol = QComboBox()
        self.binance_symbol.addItems(["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "SOLUSDT", "AVAXUSDT"])
        self.binance_symbol.setCurrentText("BTCUSDT")
        layout.addWidget(self.binance_symbol, 0, 1)
        
        # 레버리지
        layout.addWidget(QLabel("레버리지:"), 0, 2)
        self.binance_leverage = QSpinBox()
        self.binance_leverage.setRange(1, 125)
        self.binance_leverage.setValue(10)
        self.binance_leverage.setSuffix("배")
        layout.addWidget(self.binance_leverage, 0, 3)
        
        # 포지션 모드
        layout.addWidget(QLabel("포지션 모드:"), 1, 0)
        self.binance_position_mode = QComboBox()
        self.binance_position_mode.addItems(["단방향", "양방향"])
        layout.addWidget(self.binance_position_mode, 1, 1)
        
        # 마진 모드
        layout.addWidget(QLabel("마진 모드:"), 1, 2)
        self.binance_margin_mode = QComboBox()
        self.binance_margin_mode.addItems(["격리", "교차"])
        layout.addWidget(self.binance_margin_mode, 1, 3)
        
        # API 설정
        layout.addWidget(QLabel("API 키:"), 2, 0)
        self.binance_api_key = QLineEdit()
        self.binance_api_key.setPlaceholderText("바이낸스 API 키 입력")
        layout.addWidget(self.binance_api_key, 2, 1, 1, 3)

        layout.addWidget(QLabel("Secret 키:"), 3, 0)
        self.binance_secret_key = QLineEdit()
        self.binance_secret_key.setPlaceholderText("바이낸스 Secret 키 입력")
        self.binance_secret_key.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.binance_secret_key, 3, 1, 1, 2)
        
        self.binance_api_test_btn = QPushButton("연결 테스트")
        self.binance_api_test_btn.setStyleSheet("background-color: #f0b90b; color: white; font-weight: bold;")
        self.binance_api_test_btn.clicked.connect(self.test_binance_api)
        layout.addWidget(self.binance_api_test_btn, 3, 3)
        
        # 상태 정보
        status_layout = QHBoxLayout()
        self.binance_connection_status = QLabel("📊 상태: ✅ 연결됨")
        self.binance_latency = QLabel("지연시간: 45ms")
        self.binance_balance = QLabel("잔고: $50,000")
        
        status_layout.addWidget(self.binance_connection_status)
        status_layout.addWidget(self.binance_latency)
        status_layout.addWidget(self.binance_balance)
        status_layout.addStretch()
        layout.addLayout(status_layout, 3, 0, 1, 4)
        
        return tab
        
    def create_bybit_settings_tab(self):
        """바이비트 설정 탭"""
        tab = QWidget()
        layout = QGridLayout(tab)
        
        # 거래 심볼
        layout.addWidget(QLabel("거래 심볼:"), 0, 0)
        self.bybit_symbol = QComboBox()
        self.bybit_symbol.addItems(["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "SOLUSDT", "AVAXUSDT"])
        self.bybit_symbol.setCurrentText("BTCUSDT")
        layout.addWidget(self.bybit_symbol, 0, 1)
        
        # 레버리지
        layout.addWidget(QLabel("레버리지:"), 0, 2)
        self.bybit_leverage = QSpinBox()
        self.bybit_leverage.setRange(1, 100)
        self.bybit_leverage.setValue(10)
        self.bybit_leverage.setSuffix("배")
        layout.addWidget(self.bybit_leverage, 0, 3)
        
        # 포지션 모드
        layout.addWidget(QLabel("포지션 모드:"), 1, 0)
        self.bybit_position_mode = QComboBox()
        self.bybit_position_mode.addItems(["단방향", "양방향"])
        layout.addWidget(self.bybit_position_mode, 1, 1)
        
        # 마진 모드
        layout.addWidget(QLabel("마진 모드:"), 1, 2)
        self.bybit_margin_mode = QComboBox()
        self.bybit_margin_mode.addItems(["격리", "교차"])
        layout.addWidget(self.bybit_margin_mode, 1, 3)
        
        # API 설정
        layout.addWidget(QLabel("API 키:"), 2, 0)
        self.bybit_api_key = QLineEdit()
        self.bybit_api_key.setPlaceholderText("바이비트 API 키 입력")
        layout.addWidget(self.bybit_api_key, 2, 1, 1, 3)

        layout.addWidget(QLabel("Secret 키:"), 3, 0)
        self.bybit_secret_key = QLineEdit()
        self.bybit_secret_key.setPlaceholderText("바이비트 Secret 키 입력")
        self.bybit_secret_key.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.bybit_secret_key, 3, 1, 1, 2)

        self.bybit_api_test_btn = QPushButton("연결 테스트")
        self.bybit_api_test_btn.setStyleSheet("background-color: #f7931a; color: white; font-weight: bold;")
        self.bybit_api_test_btn.clicked.connect(self.test_bybit_api)
        layout.addWidget(self.bybit_api_test_btn, 3, 3)
        
        # 상태 정보
        status_layout = QHBoxLayout()
        self.bybit_connection_status = QLabel("📊 상태: ✅ 연결됨")
        self.bybit_latency = QLabel("지연시간: 38ms")
        self.bybit_balance = QLabel("잔고: $30,000")
        
        status_layout.addWidget(self.bybit_connection_status)
        status_layout.addWidget(self.bybit_latency)
        status_layout.addWidget(self.bybit_balance)
        status_layout.addStretch()
        layout.addLayout(status_layout, 3, 0, 1, 4)
        
        return tab
    
    def create_condition_combination(self, layout):
        """조건 조합 방식"""
        group = QGroupBox("🔄 조건 조합 방식")
        group_layout = QHBoxLayout(group)
        
        # 라디오 버튼 그룹
        self.combination_group = QButtonGroup()
        
        # AND 조합
        self.and_radio = QRadioButton("AND 조합 (모든 조건 충족)")
        self.and_radio.setChecked(True)
        self.and_radio.setFont(QFont("Arial", 9))
        self.and_radio.setStyleSheet("color: #333; font-weight: bold;")
        
        # OR 조합
        self.or_radio = QRadioButton("OR 조합 (하나 이상 조건 충족)")
        self.or_radio.setFont(QFont("Arial", 9))
        self.or_radio.setStyleSheet("color: #333; font-weight: bold;")
        
        self.combination_group.addButton(self.and_radio, 0)
        self.combination_group.addButton(self.or_radio, 1)
        
        group_layout.addWidget(self.and_radio)
        group_layout.addWidget(self.or_radio)
        group_layout.addStretch()
        
        layout.addWidget(group)
    
    def create_moving_average_condition(self, layout):
        """이동평균선 조건"""
        group = QGroupBox("📊 이동평균선 조건")
        group_layout = QGridLayout(group)
        
        # 활성화 체크박스
        self.ma_condition_check = QCheckBox("활성화")
        self.ma_checkbox = self.ma_condition_check  # 별칭 추가
        self.ma_condition_check.setStyleSheet("font-weight: bold; color: #007bff;")
        self.ma_condition_check.stateChanged.connect(self.on_condition_changed)
        group_layout.addWidget(self.ma_condition_check, 0, 0, 1, 2)
        
        # 조건 선택
        group_layout.addWidget(QLabel("조건:"), 1, 0)
        self.ma_condition_combo = QComboBox()
        ma_conditions = [
            "시가 > 이평선 → 매수 ↗",
            "시가 < 이평선 → 매수 ↘", 
            "시가 > 이평선 → 매도 ↘",
            "시가 < 이평선 → 매도 ↗",
            "현재가 > 이평선 → 매수 ↗",
            "현재가 < 이평선 → 매수 ↘",
            "현재가 > 이평선 → 매도 ↘", 
            "현재가 < 이평선 → 매도 ↗"
        ]
        self.ma_condition_combo.addItems(ma_conditions)
        self.ma_condition_combo.setStyleSheet("font-size: 10pt;")
        group_layout.addWidget(self.ma_condition_combo, 1, 1)
        
        # 이평선 기간 (단기/장기)
        group_layout.addWidget(QLabel("단기:"), 2, 0)
        self.ma_period_short_spin = QSpinBox()
        self.ma_short_input = self.ma_period_short_spin  # 별칭 추가
        self.ma_period_short_spin.setRange(1, 100)
        self.ma_period_short_spin.setValue(10)
        self.ma_period_short_spin.setSuffix("봉")
        group_layout.addWidget(self.ma_period_short_spin, 2, 1)

        group_layout.addWidget(QLabel("장기:"), 3, 0)
        self.ma_period_long_spin = QSpinBox()
        self.ma_long_input = self.ma_period_long_spin  # 별칭 추가
        self.ma_period_long_spin.setRange(1, 200)
        self.ma_period_long_spin.setValue(30)
        self.ma_period_long_spin.setSuffix("봉")
        group_layout.addWidget(self.ma_period_long_spin, 3, 1)
        
        layout.addWidget(group)
    
    def create_price_channel_condition(self, layout):
        """Price Channel 조건"""
        group = QGroupBox("📈 Price Channel 조건")
        group_layout = QGridLayout(group)
        
        # 활성화 체크박스
        self.pc_condition_check = QCheckBox("활성화")
        self.price_channel_checkbox = self.pc_condition_check  # 별칭 추가
        self.pc_condition_check.setStyleSheet("font-weight: bold; color: #28a745;")
        self.pc_condition_check.stateChanged.connect(self.on_condition_changed)
        group_layout.addWidget(self.pc_condition_check, 0, 0, 1, 2)
        
        # 조건 선택
        group_layout.addWidget(QLabel("조건:"), 1, 0)
        self.pc_condition_combo = QComboBox()
        pc_conditions = [
            "상단선 돌파 → 매수 ↗ (순추세)",
            "상단선 돌파 → 매도 ↘ (역추세)",
            "하단선 돌파 → 매수 ↘ (역추세)",
            "하단선 돌파 → 매도 ↗ (순추세)"
        ]
        self.pc_condition_combo.addItems(pc_conditions)
        self.pc_condition_combo.setStyleSheet("font-size: 10pt;")
        group_layout.addWidget(self.pc_condition_combo, 1, 1)
        
        # PC 기간
        group_layout.addWidget(QLabel("기간:"), 2, 0)
        self.pc_period_spin = QSpinBox()
        self.pc_period_input = self.pc_period_spin  # 별칭 추가
        self.pc_period_spin.setRange(1, 100)
        self.pc_period_spin.setValue(20)
        self.pc_period_spin.setSuffix("봉")
        group_layout.addWidget(self.pc_period_spin, 2, 1)
        
        layout.addWidget(group)
    
    def create_orderbook_watch_condition(self, layout):
        """호가 감시 조건"""
        group = QGroupBox("📋 호가 감시 조건")
        group_layout = QGridLayout(group)
        
        # 활성화 체크박스
        self.orderbook_condition_check = QCheckBox("활성화")
        self.orderbook_condition_check.setStyleSheet("font-weight: bold; color: #ffc107;")
        self.orderbook_condition_check.stateChanged.connect(self.on_condition_changed)
        group_layout.addWidget(self.orderbook_condition_check, 0, 0, 1, 2)
        
        # 상승 틱 설정
        group_layout.addWidget(QLabel("상승 틱:"), 1, 0)
        self.up_ticks_spin = QSpinBox()
        self.up_ticks_spin.setRange(0, 100)
        self.up_ticks_spin.setValue(0)
        self.up_ticks_spin.setSuffix("틱")
        group_layout.addWidget(self.up_ticks_spin, 1, 1)
        
        # 하락 틱 설정
        group_layout.addWidget(QLabel("하락 틱:"), 2, 0)
        self.down_ticks_spin = QSpinBox()
        self.down_ticks_spin.setRange(0, 100)
        self.down_ticks_spin.setValue(0)
        self.down_ticks_spin.setSuffix("틱")
        group_layout.addWidget(self.down_ticks_spin, 2, 1)
        
        # 즉시 진입 체크박스
        self.immediate_entry_check = QCheckBox("0틱 즉시 진입")
        self.immediate_entry_check.setStyleSheet("color: #dc3545; font-weight: bold;")
        group_layout.addWidget(self.immediate_entry_check, 3, 0, 1, 2)
        
        layout.addWidget(group)
    
    def create_candle_state_condition(self, layout):
        """캔들 상태 조건"""
        group = QGroupBox("🕯️ 캔들 상태 조건")
        group_layout = QGridLayout(group)
        
        # 활성화 체크박스
        self.candle_condition_check = QCheckBox("활성화")
        self.candle_condition_check.setStyleSheet("font-weight: bold; color: #6f42c1;")
        self.candle_condition_check.stateChanged.connect(self.on_condition_changed)
        group_layout.addWidget(self.candle_condition_check, 0, 0, 1, 2)
        
        # 조건 선택
        group_layout.addWidget(QLabel("조건:"), 1, 0)
        self.candle_condition_combo = QComboBox()
        candle_conditions = [
            "양봉 상태 → 매수 ↗ (순추세)",
            "양봉 상태 → 매도 ↘ (역추세)",
            "음봉 상태 → 매수 ↘ (역추세)",
            "음봉 상태 → 매도 ↗ (순추세)"
        ]
        self.candle_condition_combo.addItems(candle_conditions)
        self.candle_condition_combo.setStyleSheet("font-size: 10pt;")
        group_layout.addWidget(self.candle_condition_combo, 1, 1)
        
        # 확인 기간
        group_layout.addWidget(QLabel("확인 기간:"), 2, 0)
        self.candle_period_spin = QSpinBox()
        self.candle_period_spin.setRange(1, 10)
        self.candle_period_spin.setValue(1)
        self.candle_period_spin.setSuffix("봉")
        group_layout.addWidget(self.candle_period_spin, 2, 1)
        
        layout.addWidget(group)
    
    def create_tick_based_condition(self, layout):
        """틱 기반 추가 진입"""
        group = QGroupBox("⚡ 틱 기반 추가 진입")
        group_layout = QGridLayout(group)
        
        # 활성화 체크박스
        self.tick_condition_check = QCheckBox("활성화")
        self.tick_condition_check.setStyleSheet("font-weight: bold; color: #20c997;")
        self.tick_condition_check.stateChanged.connect(self.on_condition_changed)
        group_layout.addWidget(self.tick_condition_check, 0, 0, 1, 2)
        
        # 상승 틱 수
        group_layout.addWidget(QLabel("상승 틱:"), 1, 0)
        self.tick_up_spin = QSpinBox()
        self.tick_up_spin.setRange(1, 50)
        self.tick_up_spin.setValue(5)
        self.tick_up_spin.setSuffix("틱")
        group_layout.addWidget(self.tick_up_spin, 1, 1)
        
        # 하락 틱 수
        group_layout.addWidget(QLabel("하락 틱:"), 2, 0)
        self.tick_down_spin = QSpinBox()
        self.tick_down_spin.setRange(1, 50)
        self.tick_down_spin.setValue(5)
        self.tick_down_spin.setSuffix("틱")
        group_layout.addWidget(self.tick_down_spin, 2, 1)
        
        # 추가 진입 비중
        group_layout.addWidget(QLabel("추가 비중:"), 3, 0)
        self.additional_ratio_spin = QSpinBox()
        self.additional_ratio_spin.setRange(10, 100)
        self.additional_ratio_spin.setValue(50)
        self.additional_ratio_spin.setSuffix("%")
        group_layout.addWidget(self.additional_ratio_spin, 3, 1)
        
        layout.addWidget(group)
    
    def add_entry_separator(self, layout):
        """구분선 추가"""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #dee2e6; margin: 5px 0;")
        layout.addWidget(separator)
    
    def create_frame_layout(self, inner_layout):
        """프레임으로 감싼 레이아웃 생성"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 5px;")
        frame.setLayout(inner_layout)
        return frame
    
    def update_monitoring_data(self):
        """실시간 모니터링 데이터 업데이트"""
        try:
            # 현재가 정보 업데이트
            self.current_price_label.setText(f"현재가: {self.market_data['current_price']:,}")
            self.ma_value_label.setText(f"이평선: {self.market_data['ma_value']:,}")
            self.signal_count_label.setText(f"신호 발생: {self.market_data['signal_count']}개")
            
            # PC 범위 정보 업데이트
            self.pc_range_label.setText(f"PC 범위: {self.market_data['pc_lower']:,} ~ {self.market_data['pc_upper']:,}")
            
            # 조건별 상태 업데이트
            self.update_condition_status()
            
        except Exception as e:
            logger.error(f"모니터링 데이터 업데이트 오류: {e}")
    
    def update_condition_status(self):
        """조건별 상태 업데이트"""
        try:
            # 각 조건의 활성화 상태에 따라 상태 업데이트
            conditions = {
                "📊 이동평균선": (self.ma_condition_check.isChecked(), "매수 조건 만족" if self.ma_condition_check.isChecked() else "비활성"),
                "📈 Price Channel": (self.pc_condition_check.isChecked(), "조건 대기중" if self.pc_condition_check.isChecked() else "비활성"),
                "🔔 호가 감지": (self.orderbook_condition_check.isChecked(), "감시 중" if self.orderbook_condition_check.isChecked() else "비활성"),
                "🕯 캔들 상태": (self.candle_condition_check.isChecked(), "상태 확인 중" if self.candle_condition_check.isChecked() else "비활성"),
                "📈 틱 기반": (self.tick_condition_check.isChecked(), "패턴 감지 중" if self.tick_condition_check.isChecked() else "비활성")
            }
            
            for condition_name, (is_active, status_text) in conditions.items():
                if condition_name in self.condition_status_labels:
                    condition_label, status_label = self.condition_status_labels[condition_name]
                    
                    if is_active:
                        condition_label.setText(f"{condition_name}: {status_text}")
                        status_label.setText("✅" if "만족" in status_text else "⏳")
                    else:
                        condition_label.setText(f"{condition_name}: 비활성")
                        status_label.setText("⏸")
            
        except Exception as e:
            logger.error(f"조건 상태 업데이트 오류: {e}")
    
    def get_settings(self) -> Dict[str, Any]:
        """현재 설정값 반환"""
        return {
            'exchanges': {
                'binance_enabled': self.binance_check.isChecked(),
                'bybit_enabled': self.bybit_check.isChecked(),
                'dual_mode': self.dual_mode_check.isChecked()
            },
            'combination': {
                'mode': 'AND' if self.and_radio.isChecked() else 'OR'
            },
            'conditions': {
                'moving_average': {
                    'enabled': self.ma_condition_check.isChecked(),
                    'condition': self.ma_condition_combo.currentText(),
                    'short_period': self.ma_period_short_spin.value(),
                    'long_period': self.ma_period_long_spin.value()
                },
                'price_channel': {
                    'enabled': self.pc_condition_check.isChecked(),
                    'condition': self.pc_condition_combo.currentText(),
                    'period': self.pc_period_spin.value()
                },
                'orderbook_watch': {
                    'enabled': self.orderbook_condition_check.isChecked(),
                    'up_ticks': self.up_ticks_spin.value(),
                    'down_ticks': self.down_ticks_spin.value(),
                    'immediate_entry': self.immediate_entry_check.isChecked()
                },
                'candle_state': {
                    'enabled': self.candle_condition_check.isChecked(),
                    'condition': self.candle_condition_combo.currentText(),
                    'period': self.candle_period_spin.value()
                },
                'tick_based': {
                    'enabled': self.tick_condition_check.isChecked(),
                    'up_ticks': self.tick_up_spin.value(),
                    'down_ticks': self.tick_down_spin.value(),
                    'additional_ratio': self.additional_ratio_spin.value()
                }
            }
        }
    
    def load_settings(self, settings: Dict[str, Any]):
        """설정값 로드"""
        try:
            # API 키 로드 (config.json에서)
            from config.settings_manager import get_settings_manager
            settings_manager = get_settings_manager()

            # Binance API 키 로드
            binance_config = settings_manager.get_exchange_config("binance")
            if binance_config:
                self.binance_api_key.setText(binance_config.api_key)
                self.binance_secret_key.setText(binance_config.api_secret)

            # Bybit API 키 로드
            bybit_config = settings_manager.get_exchange_config("bybit")
            if bybit_config:
                self.bybit_api_key.setText(bybit_config.api_key)
                self.bybit_secret_key.setText(bybit_config.api_secret)

            # 거래소 설정
            exchanges = settings.get('exchanges', {})
            self.binance_check.setChecked(exchanges.get('binance_enabled', True))
            self.bybit_check.setChecked(exchanges.get('bybit_enabled', True))
            self.dual_mode_check.setChecked(exchanges.get('dual_mode', True))
            
            # 조합 방식
            combination = settings.get('combination', {})
            if combination.get('mode') == 'OR':
                self.or_radio.setChecked(True)
            else:
                self.and_radio.setChecked(True)
            
            # 조건 설정
            conditions = settings.get('conditions', {})
            
            # 이동평균선 조건
            ma_settings = conditions.get('moving_average', {})
            self.ma_condition_check.setChecked(ma_settings.get('enabled', False))
            if 'condition' in ma_settings:
                self.ma_condition_combo.setCurrentText(ma_settings['condition'])
            self.ma_period_short_spin.setValue(ma_settings.get('short_period', 10))
            self.ma_period_long_spin.setValue(ma_settings.get('long_period', 30))
            
            # Price Channel 조건
            pc_settings = conditions.get('price_channel', {})
            self.pc_condition_check.setChecked(pc_settings.get('enabled', False))
            if 'condition' in pc_settings:
                self.pc_condition_combo.setCurrentText(pc_settings['condition'])
            self.pc_period_spin.setValue(pc_settings.get('period', 20))
            
            # 호가 감시 조건
            orderbook_settings = conditions.get('orderbook_watch', {})
            self.orderbook_condition_check.setChecked(orderbook_settings.get('enabled', False))
            self.up_ticks_spin.setValue(orderbook_settings.get('up_ticks', 0))
            self.down_ticks_spin.setValue(orderbook_settings.get('down_ticks', 0))
            self.immediate_entry_check.setChecked(orderbook_settings.get('immediate_entry', False))
            
            # 캔들 상태 조건
            candle_settings = conditions.get('candle_state', {})
            self.candle_condition_check.setChecked(candle_settings.get('enabled', False))
            if 'condition' in candle_settings:
                self.candle_condition_combo.setCurrentText(candle_settings['condition'])
            self.candle_period_spin.setValue(candle_settings.get('period', 1))
            
            # 틱 기반 조건
            tick_settings = conditions.get('tick_based', {})
            self.tick_condition_check.setChecked(tick_settings.get('enabled', False))
            self.tick_up_spin.setValue(tick_settings.get('up_ticks', 5))
            self.tick_down_spin.setValue(tick_settings.get('down_ticks', 5))
            self.additional_ratio_spin.setValue(tick_settings.get('additional_ratio', 50))
            
            logger.info("진입 설정 탭 설정값 로드 완료")

        except Exception as e:
            logger.error(f"설정값 로드 오류: {e}")

    def test_binance_api(self):
        """바이낸스 API 연결 테스트"""
        try:
            api_key = self.binance_api_key.text().strip()
            secret_key = self.binance_secret_key.text().strip()

            if not api_key or not secret_key:
                QMessageBox.warning(
                    self,
                    "API 키 필요",
                    "바이낸스 API 키와 Secret 키를 입력해주세요."
                )
                return

            # 설정에서 testnet 여부 확인
            settings_manager = get_settings_manager()
            binance_config = settings_manager.get_exchange_config("binance")
            testnet = binance_config.testnet if binance_config else False

            # 디버그 로깅
            logger.info(f"Binance config: {binance_config}")
            logger.info(f"Testnet 설정값: {testnet}")
            print(f"[DEBUG] Binance testnet: {testnet}")

            # 테스트 다이얼로그 표시
            dialog = APITestDialog(
                self,
                exchange="Binance",
                api_key=api_key,
                secret_key=secret_key,
                testnet=testnet
            )
            dialog.exec_()

            # 테스트 완료 후 상태 업데이트
            # 실제 연결 상태에 따라 UI 업데이트
            self._update_connection_status('binance', dialog.test_successful if hasattr(dialog, 'test_successful') else False)

        except Exception as e:
            logger.error(f"바이낸스 API 테스트 오류: {e}")
            QMessageBox.critical(
                self,
                "테스트 오류",
                f"API 테스트 중 오류가 발생했습니다:\n{str(e)}"
            )

    def test_bybit_api(self):
        """바이비트 API 연결 테스트"""
        try:
            api_key = self.bybit_api_key.text().strip()
            secret_key = self.bybit_secret_key.text().strip()

            if not api_key or not secret_key:
                QMessageBox.warning(
                    self,
                    "API 키 필요",
                    "바이비트 API 키와 Secret 키를 입력해주세요."
                )
                return

            # 설정에서 testnet 여부 확인
            settings_manager = get_settings_manager()
            bybit_config = settings_manager.get_exchange_config("bybit")
            testnet = bybit_config.testnet if bybit_config else False

            # 테스트 다이얼로그 표시
            dialog = APITestDialog(
                self,
                exchange="Bybit",
                api_key=api_key,
                secret_key=secret_key,
                testnet=testnet
            )
            dialog.exec_()

            # 테스트 완료 후 상태 업데이트
            # TODO: 실제 연결 상태에 따라 UI 업데이트

        except Exception as e:
            logger.error(f"바이비트 API 테스트 오류: {e}")
            QMessageBox.critical(
                self,
                "테스트 오류",
                f"API 테스트 중 오류가 발생했습니다:\n{str(e)}"
            )

    def _update_connection_status(self, exchange: str, is_connected: bool):
        """연결 상태 UI 업데이트

        Args:
            exchange: 거래소 이름 ('binance' 또는 'bybit')
            is_connected: 연결 성공 여부
        """
        if exchange == 'binance':
            status_label = "✓ 연결됨" if is_connected else "✗ 연결 안됨"
            color = "green" if is_connected else "red"
            # 바이낸스 체크박스 옆에 상태 표시
            if hasattr(self, 'binance_checkbox'):
                self.binance_checkbox.setText(f"바이낸스 {status_label}")
                self.binance_checkbox.setStyleSheet(f"color: {color};")
        elif exchange == 'bybit':
            status_label = "✓ 연결됨" if is_connected else "✗ 연결 안됨"
            color = "green" if is_connected else "red"
            # 바이비트 체크박스 옆에 상태 표시
            if hasattr(self, 'bybit_checkbox'):
                self.bybit_checkbox.setText(f"바이비트 {status_label}")
                self.bybit_checkbox.setStyleSheet(f"color: {color};")

    def connect_condition_signals(self):
        """조건 변경 시그널 연결"""
        # 조건 조합 방식 변경시 (라디오 버튼)
        self.and_radio.toggled.connect(self.update_trading_conditions)
        self.or_radio.toggled.connect(self.update_trading_conditions)

        # 각 조건의 상세 설정 변경시
        # 이동평균선
        self.ma_period_short_spin.valueChanged.connect(self.update_trading_conditions)
        self.ma_period_long_spin.valueChanged.connect(self.update_trading_conditions)
        self.ma_condition_combo.currentTextChanged.connect(self.update_trading_conditions)

        # Price Channel
        self.pc_period_spin.valueChanged.connect(self.update_trading_conditions)
        self.pc_condition_combo.currentTextChanged.connect(self.update_trading_conditions)

        # 호가 감시
        self.up_ticks_spin.valueChanged.connect(self.update_trading_conditions)
        self.down_ticks_spin.valueChanged.connect(self.update_trading_conditions)

        # 캤들 상태
        self.candle_period_spin.valueChanged.connect(self.update_trading_conditions)
        self.candle_condition_combo.currentTextChanged.connect(self.update_trading_conditions)

        # 틱 기반
        self.tick_up_spin.valueChanged.connect(self.update_trading_conditions)
        self.tick_down_spin.valueChanged.connect(self.update_trading_conditions)
        self.additional_ratio_spin.valueChanged.connect(self.update_trading_conditions)

    def on_condition_changed(self, state):
        """조건 체크박스 상태 변경 처리"""
        logger.info(f"체크박스 상태 변경: state={state}")
        self.update_trading_conditions()

    def update_monitoring_data(self):
        """실시간 모니터링 데이터 업데이트"""
        try:
            # 메인 윈도우에서 API 클라이언트 가져오기
            main_window = self.parent()
            if not main_window:
                return

            # Binance 클라이언트 확인
            if hasattr(main_window, 'binance_client') and main_window.binance_client:
                try:
                    # 현재가 조회
                    ticker = main_window.binance_client.get_ticker("BTCUSDT")
                    if ticker:
                        current_price = ticker.price
                        self.current_price_label.setText(f"현재가: {current_price:,.0f}")
                        self.market_data['current_price'] = current_price

                        # Price Channel 계산 (간단한 예시)
                        pc_upper = current_price * 1.01  # 1% 위
                        pc_lower = current_price * 0.99  # 1% 아래
                        self.pc_range_label.setText(f"PC 범위: {pc_lower:,.0f} ~ {pc_upper:,.0f}")
                        self.market_data['pc_upper'] = pc_upper
                        self.market_data['pc_lower'] = pc_lower

                        # MA 값 (간단한 예시 - 실제로는 과거 데이터 필요)
                        ma_value = current_price * 0.995  # 예시값
                        self.ma_value_label.setText(f"이평선: {ma_value:,.0f}")
                        self.market_data['ma_value'] = ma_value

                except Exception as e:
                    logger.debug(f"API 데이터 업데이트 실패: {e}")

            # 신호 개수 업데이트
            signal_count = self.market_data.get('signal_count', 0)
            self.signal_count_label.setText(f"신호 발생: {signal_count}개")

        except Exception as e:
            logger.error(f"모니터링 데이터 업데이트 오류: {e}")

    def update_trading_conditions(self):
        """거래 엔진에 조건 업데이트"""
        logger.info("update_trading_conditions 호출됨")
        if not self.trading_engine:
            logger.warning("거래 엔진이 설정되지 않았습니다 - Trading Engine이 None입니다!")
            return

        try:
            # 기존 조건 모두 제거
            self.trading_engine.entry_conditions.clear()

            # 활성화된 조건들 수집
            active_conditions = []

            # 이동평균선 조건
            if self.ma_condition_check.isChecked():
                config = {
                    "type": "ma_cross",
                    "enabled": True,
                    "params": {
                        "short_period": self.ma_period_short_spin.value(),
                        "long_period": self.ma_period_long_spin.value(),
                        "condition_type": self.ma_condition_combo.currentText()
                    }
                }
                active_conditions.append(config)

            # Price Channel 조건
            if self.pc_condition_check.isChecked():
                config = {
                    "type": "price_channel",
                    "enabled": True,
                    "params": {
                        "period": self.pc_period_spin.value(),
                        "condition_type": self.pc_condition_combo.currentText()
                    }
                }
                active_conditions.append(config)

            # 호가 감시 조건
            if self.orderbook_condition_check.isChecked():
                config = {
                    "type": "orderbook_watch",
                    "enabled": True,
                    "params": {
                        "up_ticks": self.up_ticks_spin.value(),
                        "down_ticks": self.down_ticks_spin.value(),
                        "immediate_entry": self.immediate_entry_check.isChecked()
                    }
                }
                active_conditions.append(config)

            # 캤들 상태 조건
            if self.candle_condition_check.isChecked():
                config = {
                    "type": "candle_state",
                    "enabled": True,
                    "params": {
                        "period": self.candle_period_spin.value(),
                        "condition_type": self.candle_condition_combo.currentText()
                    }
                }
                active_conditions.append(config)

            # 틱 기반 조건
            if self.tick_condition_check.isChecked():
                config = {
                    "type": "tick_based",
                    "enabled": True,
                    "params": {
                        "up_ticks": self.tick_up_spin.value(),
                        "down_ticks": self.tick_down_spin.value(),
                        "additional_ratio": self.additional_ratio_spin.value()
                    }
                }
                active_conditions.append(config)

            # 조건 조합 방식 (AND or OR)
            combination_mode = "AND" if self.and_radio.isChecked() else "OR"

            # 거래 엔진에 조건 조합 방식 설정
            if hasattr(self.trading_engine, 'set_combination_mode'):
                self.trading_engine.set_combination_mode(combination_mode)

            # 거래 엔진에 조건 추가
            from conditions.condition_factory import ConditionFactory

            logger.info(f"조건 추가 시작: {len(active_conditions)}개")
            for config in active_conditions:
                try:
                    condition = ConditionFactory.create_condition(config)
                    self.trading_engine.add_entry_condition(condition)
                    logger.info(f"조건 추가 성공: {config['type']} - {condition.get_name()}")
                except Exception as e:
                    logger.error(f"조건 생성 실패: {config['type']} - {e}")

            # 조건 변경 시그널 발송
            self.condition_changed.emit(
                f"{len(active_conditions)}개 조건",
                len(active_conditions) > 0
            )

            logger.info(f"거래 조건 업데이트: {len(active_conditions)}개 조건, 조합 방식: {combination_mode}")

        except Exception as e:
            logger.error(f"거래 조건 업데이트 실패: {e}")

    def connect_signals(self):
        """위젯 시그널 연결"""
        # MA Cross 관련
        if hasattr(self, 'ma_checkbox'):
            self.ma_checkbox.stateChanged.connect(self.update_ma_cross)
        if hasattr(self, 'ma_short_input'):
            self.ma_short_input.valueChanged.connect(self.update_ma_cross)
        if hasattr(self, 'ma_long_input'):
            self.ma_long_input.valueChanged.connect(self.update_ma_cross)

        # Price Channel 관련
        if hasattr(self, 'price_channel_checkbox'):
            self.price_channel_checkbox.stateChanged.connect(self.update_price_channel)
        if hasattr(self, 'pc_period_input'):
            self.pc_period_input.valueChanged.connect(self.update_price_channel)

        # 조합 모드 관련
        if hasattr(self, 'and_radio'):
            self.and_radio.toggled.connect(self.update_combination_mode)
        if hasattr(self, 'or_radio'):
            self.or_radio.toggled.connect(self.update_combination_mode)

    def update_ma_cross(self):
        """MA Cross 조건 업데이트"""
        if self.trading_engine and hasattr(self, 'ma_checkbox'):
            if self.ma_checkbox.isChecked():
                # MA Cross 조건 추가
                config = {
                    "type": "ma_cross",
                    "enabled": True,
                    "params": {
                        "short_period": self.ma_short_input.value() if hasattr(self, 'ma_short_input') else 10,
                        "long_period": self.ma_long_input.value() if hasattr(self, 'ma_long_input') else 30
                    }
                }
                from conditions.condition_factory import ConditionFactory
                condition = ConditionFactory.create_condition(config)
                self.trading_engine.add_entry_condition(condition)

    def update_price_channel(self):
        """Price Channel 조건 업데이트"""
        if self.trading_engine and hasattr(self, 'price_channel_checkbox'):
            if self.price_channel_checkbox.isChecked():
                # Price Channel 조건 추가
                config = {
                    "type": "price_channel",
                    "enabled": True,
                    "params": {
                        "period": self.pc_period_input.value() if hasattr(self, 'pc_period_input') else 20
                    }
                }
                from conditions.condition_factory import ConditionFactory
                condition = ConditionFactory.create_condition(config)
                self.trading_engine.add_entry_condition(condition)

    def update_combination_mode(self):
        """조건 조합 모드 업데이트"""
        if self.trading_engine:
            mode = "AND" if self.and_radio.isChecked() else "OR"
            if hasattr(self.trading_engine, 'set_combination_mode'):
                self.trading_engine.set_combination_mode(mode)

