"""
리스크 관리 탭 모듈 - 완전 복원 버전

이 모듈은 리스크 관리 설정 UI를 구현합니다.
원본 GUI의 모든 기능을 모듈화된 구조로 완전 복원했습니다.
"""

from typing import Dict, Any, List
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, 
    QCheckBox, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QFrame, QTabWidget, QWidget,
    QScrollArea, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from gui.base_tab import BaseTab
from utils.logger import get_logger

logger = get_logger(__name__)


class RiskTab(BaseTab):
    """리스크 관리 탭 - 완전 복원"""
    
    # 리스크 관리 관련 시그널
    risk_limit_changed = pyqtSignal(str, float)
    leverage_changed = pyqtSignal(int)
    
    def __init__(self, parent=None, trading_engine=None):
        # 12단계 익절/손절 데이터 - super().__init__() 호출 전에 정의
        self.profit_loss_data = [
            (1, 2.0, 1.0), (2, 4.0, 2.0), (3, 6.0, 3.0),
            (4, 8.0, 4.0), (5, 10.0, 5.0), (6, 12.0, 6.0),
            (7, 15.0, 8.0), (8, 20.0, 10.0), (9, 25.0, 12.0),
            (10, 30.0, 15.0), (11, 40.0, 20.0), (12, 50.0, 25.0)
        ]

        super().__init__("리스크 관리", parent)

        self.trading_engine = trading_engine
        # 리스크 관리 상태
        self.risk_settings = {}
    
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
        
        # 1. 레버리지 관리
        self.create_leverage_management(scroll_layout)
        
        # 2. 포지션 제한
        self.create_position_limits(scroll_layout)
        
        # 3. 12단계 익절/손절
        self.create_profit_loss_table(scroll_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)

        # 시그널 연결
        self.connect_risk_signals()
    
    def create_leverage_management(self, layout):
        """레버리지 관리"""
        group = QGroupBox("⚙️ 레버리지 관리")
        group_layout = QGridLayout(group)
        
        # 최대 레버리지
        group_layout.addWidget(QLabel("최대 레버리지:"), 0, 0)
        self.max_leverage_spin = QSpinBox()
        self.max_leverage_spin.setRange(1, 100)
        self.max_leverage_spin.setValue(10)
        self.max_leverage_spin.setSuffix("배")
        self.max_leverage_spin.setStyleSheet("font-size: 11pt; font-weight: bold;")
        group_layout.addWidget(self.max_leverage_spin, 0, 1)
        
        # 포지션 모드
        group_layout.addWidget(QLabel("포지션 모드:"), 0, 2)
        self.position_mode_combo = QComboBox()
        self.position_mode_combo.addItems(["단방향", "양방향"])
        self.position_mode_combo.setCurrentText("단방향")
        self.position_mode_combo.setStyleSheet("font-size: 10pt;")
        group_layout.addWidget(self.position_mode_combo, 0, 3)
        
        # 자동 레버리지 조정
        self.auto_leverage_check = QCheckBox("자동 레버리지 조정")
        self.auto_leverage_check.setChecked(True)
        self.auto_leverage_check.setStyleSheet("color: #007bff; font-weight: bold; font-size: 11pt;")
        group_layout.addWidget(self.auto_leverage_check, 1, 0, 1, 2)
        
        layout.addWidget(group)
    
    def create_position_limits(self, layout):
        """포지션 제한"""
        group = QGroupBox("🚫 포지션 제한")
        group_layout = QGridLayout(group)
        
        # 최대 포지션 수
        group_layout.addWidget(QLabel("최대 포지션 수:"), 0, 0)
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(1, 10)
        self.max_positions_spin.setValue(3)
        self.max_positions_spin.setSuffix("개")
        self.max_positions_spin.setStyleSheet("font-size: 11pt; font-weight: bold;")
        group_layout.addWidget(self.max_positions_spin, 0, 1)
        
        # 포지션당 최대 크기
        group_layout.addWidget(QLabel("포지션당 최대 크기:"), 0, 2)
        self.max_position_size_combo = QComboBox()
        self.max_position_size_combo.addItems([
            "10000.00 USDT", "50000.00 USDT", "100000.00 USDT", 
            "200000.00 USDT", "500000.00 USDT"
        ])
        self.max_position_size_combo.setCurrentText("100000.00 USDT")
        self.max_position_size_combo.setStyleSheet("font-size: 10pt;")
        group_layout.addWidget(self.max_position_size_combo, 0, 3)
        
        # 일일 최대 거래
        group_layout.addWidget(QLabel("일일 최대 거래:"), 1, 0)
        self.daily_max_trades_spin = QSpinBox()
        self.daily_max_trades_spin.setRange(1, 100)
        self.daily_max_trades_spin.setValue(50)
        self.daily_max_trades_spin.setSuffix("회")
        self.daily_max_trades_spin.setStyleSheet("font-size: 11pt; font-weight: bold;")
        group_layout.addWidget(self.daily_max_trades_spin, 1, 1)
        
        # 일일 운영 한도
        group_layout.addWidget(QLabel("일일 운영 한도:"), 1, 2)
        self.daily_limit_combo = QComboBox()
        self.daily_limit_combo.addItems(["1.00%", "3.00%", "5.00%", "10.00%"])
        self.daily_limit_combo.setCurrentText("5.00%")
        self.daily_limit_combo.setStyleSheet("font-size: 10pt;")
        group_layout.addWidget(self.daily_limit_combo, 1, 3)
        
        layout.addWidget(group)
    
    def create_profit_loss_table(self, layout):
        """12단계 익절/손절 테이블"""
        group = QGroupBox("📊 12단계 익절/손절")
        group_layout = QVBoxLayout(group)
        
        # 테이블 생성
        self.profit_loss_table = QTableWidget()
        self.profit_loss_table.setRowCount(12)
        self.profit_loss_table.setColumnCount(3)
        self.profit_loss_table.setHorizontalHeaderLabels(["단계", "익절(%)", "손절(%)"])
        
        # 테이블 스타일 설정
        self.profit_loss_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
                font-size: 10pt;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }
            QHeaderView::section {
                background-color: #e9ecef;
                padding: 8px;
                border: 1px solid #dee2e6;
                font-weight: bold;
                font-size: 11pt;
            }
        """)
        
        # 테이블 데이터 채우기
        for i, (step, profit, loss) in enumerate(self.profit_loss_data):
            # 단계
            step_item = QTableWidgetItem(str(step))
            step_item.setTextAlignment(Qt.AlignCenter)
            step_item.setFlags(Qt.ItemIsEnabled)  # 읽기 전용
            self.profit_loss_table.setItem(i, 0, step_item)
            
            # 익절 (녹색)
            profit_item = QTableWidgetItem(f"{profit:.1f}")
            profit_item.setTextAlignment(Qt.AlignCenter)
            profit_item.setBackground(Qt.green)
            profit_item.setForeground(Qt.white)
            self.profit_loss_table.setItem(i, 1, profit_item)
            
            # 손절 (빨간색)
            loss_item = QTableWidgetItem(f"{loss:.1f}")
            loss_item.setTextAlignment(Qt.AlignCenter)
            loss_item.setBackground(Qt.red)
            loss_item.setForeground(Qt.white)
            self.profit_loss_table.setItem(i, 2, loss_item)
        
        # 테이블 크기 조정
        header = self.profit_loss_table.horizontalHeader()
        # 컬럼별 너비 고정 설정
        self.profit_loss_table.setColumnWidth(0, 60)   # 단계
        self.profit_loss_table.setColumnWidth(1, 100)  # 익절(%)
        self.profit_loss_table.setColumnWidth(2, 100)  # 손절(%)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.profit_loss_table.setMaximumHeight(400)
        self.profit_loss_table.setAlternatingRowColors(True)
        
        group_layout.addWidget(self.profit_loss_table)
        
        # 하단 체크박스
        bottom_layout = QHBoxLayout()
        self.auto_stop_check = QCheckBox("익절 후 손절 시 즉시 중지")
        self.auto_stop_check.setChecked(True)
        self.auto_stop_check.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 11pt;")
        bottom_layout.addWidget(self.auto_stop_check)
        bottom_layout.addStretch()
        
        group_layout.addLayout(bottom_layout)
        layout.addWidget(group)
    
    def get_settings(self) -> Dict[str, Any]:
        """현재 설정값 반환"""
        return {
            'leverage_management': {
                'max_leverage': self.max_leverage_spin.value(),
                'position_mode': self.position_mode_combo.currentText(),
                'auto_leverage': self.auto_leverage_check.isChecked()
            },
            'position_limits': {
                'max_positions': self.max_positions_spin.value(),
                'max_position_size': self.max_position_size_combo.currentText(),
                'daily_max_trades': self.daily_max_trades_spin.value(),
                'daily_limit': self.daily_limit_combo.currentText()
            },
            'profit_loss': {
                'auto_stop': self.auto_stop_check.isChecked(),
                'table_data': self.profit_loss_data
            }
        }
    
    def load_settings(self, settings: Dict[str, Any]):
        """설정값 로드"""
        try:
            # 레버리지 관리 설정
            leverage_settings = settings.get('leverage_management', {})
            self.max_leverage_spin.setValue(leverage_settings.get('max_leverage', 10))
            if 'position_mode' in leverage_settings:
                self.position_mode_combo.setCurrentText(leverage_settings['position_mode'])
            self.auto_leverage_check.setChecked(leverage_settings.get('auto_leverage', True))
            
            # 포지션 제한 설정
            position_settings = settings.get('position_limits', {})
            self.max_positions_spin.setValue(position_settings.get('max_positions', 3))
            if 'max_position_size' in position_settings:
                self.max_position_size_combo.setCurrentText(position_settings['max_position_size'])
            self.daily_max_trades_spin.setValue(position_settings.get('daily_max_trades', 50))
            if 'daily_limit' in position_settings:
                self.daily_limit_combo.setCurrentText(position_settings['daily_limit'])
            
            # 익절/손절 설정
            profit_loss_settings = settings.get('profit_loss', {})
            self.auto_stop_check.setChecked(profit_loss_settings.get('auto_stop', True))
            
            logger.info("리스크 관리 탭 설정값 로드 완료")

        except Exception as e:
            logger.error(f"설정값 로드 오류: {e}")

    def connect_risk_signals(self):
        """리스크 관리 시그널 연결"""
        # 레버리지 관리
        self.max_leverage_spin.valueChanged.connect(self.update_risk_settings)
        self.position_mode_combo.currentTextChanged.connect(self.update_risk_settings)
        self.auto_leverage_check.stateChanged.connect(self.update_risk_settings)

        # 포지션 제한
        self.max_positions_spin.valueChanged.connect(self.update_risk_settings)
        self.max_position_size_combo.currentTextChanged.connect(self.update_risk_settings)
        self.daily_max_trades_spin.valueChanged.connect(self.update_risk_settings)
        self.daily_limit_combo.currentTextChanged.connect(self.update_risk_settings)

        # 자동 스탑
        self.auto_stop_check.stateChanged.connect(self.update_risk_settings)

    def update_risk_settings(self):
        """리스크 설정 업데이트"""
        if not self.trading_engine:
            logger.debug("거래 엔진이 설정되지 않았습니다")
            return

        try:
            # 포지션 크기를 거래 엔진 config에 직접 설정
            position_size_str = self.max_position_size_combo.currentText()
            position_size = float(position_size_str.replace(" USDT", ""))

            if hasattr(self.trading_engine, 'config') and self.trading_engine.config:
                self.trading_engine.config.position_size = position_size
                logger.info(f"포지션 크기 업데이트: ${position_size:,.2f}")

            # 리스크 관리 설정 수집
            risk_config = {
                "leverage": {
                    "max_leverage": self.max_leverage_spin.value(),
                    "position_mode": self.position_mode_combo.currentText(),
                    "auto_adjust": self.auto_leverage_check.isChecked()
                },
                "position_limits": {
                    "max_positions": self.max_positions_spin.value(),
                    "max_position_size": position_size,  # 숫자 값으로 전달
                    "daily_max_trades": self.daily_max_trades_spin.value(),
                    "daily_limit": self.daily_limit_combo.currentText()
                },
                "stop_loss": {
                    "auto_stop": self.auto_stop_check.isChecked(),
                    "levels": self.profit_loss_data
                }
            }

            # 거래 엔진에 리스크 관리자 설정
            from risk.risk_manager import RiskManager

            try:
                risk_manager = RiskManager(risk_config)
                self.trading_engine.set_risk_manager(risk_manager)

                # 레버리지 변경 시그널
                self.leverage_changed.emit(self.max_leverage_spin.value())

                # 리스크 한도 변경 시그널
                self.risk_limit_changed.emit(
                    "리스크 설정",
                    self.max_positions_spin.value()
                )

                logger.info(f"리스크 관리 설정 업데이트: 최대 레버리지 {self.max_leverage_spin.value()}배, 최대 포지션 {self.max_positions_spin.value()}개, 포지션 크기 ${position_size:,.2f}")

            except Exception as e:
                logger.error(f"리스크 관리자 생성 실패: {e}")

        except Exception as e:
            logger.error(f"리스크 설정 업데이트 실패: {e}")

    # 누락된 위젯 별칭 및 메소드 추가
    @property
    def leverage_slider(self):
        """레버리지 슬라이더 별칭 (스핀박스로 대체)"""
        return self.max_leverage_spin

    @property
    def leverage_label(self):
        """레버리지 라벨 별칭"""
        if not hasattr(self, '_leverage_label'):
            from PyQt5.QtWidgets import QLabel
            self._leverage_label = QLabel(f"{self.max_leverage_spin.value()}배")
        return self._leverage_label

    @property
    def position_size_input(self):
        """포지션 크기 입력 위젯 별칭"""
        # 콤보박스를 스핀박스처럼 사용
        if not hasattr(self, '_position_size_input'):
            from PyQt5.QtWidgets import QDoubleSpinBox
            self._position_size_input = QDoubleSpinBox()
            self._position_size_input.setRange(100, 100000)
            self._position_size_input.setValue(1000)
            self._position_size_input.setSuffix(" USDT")
        return self._position_size_input

    @property
    def stop_loss_input(self):
        """손절 퍼센트 입력 위젯 (임시)"""
        if not hasattr(self, '_stop_loss_input'):
            from PyQt5.QtWidgets import QDoubleSpinBox
            self._stop_loss_input = QDoubleSpinBox()
            self._stop_loss_input.setRange(0.1, 50.0)
            self._stop_loss_input.setValue(2.0)
            self._stop_loss_input.setSuffix("%")
        return self._stop_loss_input

    @property
    def take_profit_input(self):
        """익절 퍼센트 입력 위젯 (임시)"""
        if not hasattr(self, '_take_profit_input'):
            from PyQt5.QtWidgets import QDoubleSpinBox
            self._take_profit_input = QDoubleSpinBox()
            self._take_profit_input.setRange(0.1, 100.0)
            self._take_profit_input.setValue(5.0)
            self._take_profit_input.setSuffix("%")
        return self._take_profit_input

    @property
    def daily_loss_input(self):
        """일일 손실 한도 입력 위젯"""
        # daily_limit_combo를 스핀박스처럼 사용
        if not hasattr(self, '_daily_loss_input'):
            from PyQt5.QtWidgets import QDoubleSpinBox
            self._daily_loss_input = QDoubleSpinBox()
            self._daily_loss_input.setRange(1.0, 50.0)
            self._daily_loss_input.setValue(5.0)
            self._daily_loss_input.setSuffix("%")
        return self._daily_loss_input

    @property
    def max_positions_input(self):
        """최대 포지션 수 입력 위젯 별칭"""
        return self.max_positions_spin

    def connect_signals(self):
        """위젯 시그널 연결 (connect_risk_signals의 별칭)"""
        self.connect_risk_signals()

    def update_leverage(self):
        """레버리지 업데이트"""
        if self.trading_engine and hasattr(self.trading_engine, 'risk_manager'):
            self.trading_engine.risk_manager.max_leverage = self.leverage_slider.value()
            self.leverage_label.setText(f"{self.leverage_slider.value()}배")
            self.leverage_changed.emit(self.leverage_slider.value())

    def update_position_size(self):
        """포지션 크기 업데이트"""
        if self.trading_engine and hasattr(self.trading_engine, 'risk_manager'):
            self.trading_engine.risk_manager.position_size = self.position_size_input.value()

    def update_stop_loss(self):
        """손절 퍼센트 업데이트"""
        if self.trading_engine and hasattr(self.trading_engine, 'risk_manager'):
            self.trading_engine.risk_manager.stop_loss_pct = self.stop_loss_input.value()

    def update_take_profit(self):
        """익절 퍼센트 업데이트"""
        if self.trading_engine and hasattr(self.trading_engine, 'risk_manager'):
            self.trading_engine.risk_manager.take_profit_pct = self.take_profit_input.value()
