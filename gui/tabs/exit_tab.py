"""
ExitTab: PRD 기준 4가지 청산조건 구현

PRD에서 요구한 청산조건 4가지:
1. PCS 청산 (12단계 + 1STEP/2STEP)
2. PC 트레일링(PCT) 청산 (최종 안전장치)
3. 호가 청산 (빠른 대응)
4. PC 본절 청산 (2단계 시스템)
"""

from typing import Dict, Any, List
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QCheckBox, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QFrame, QWidget, QScrollArea, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor

from gui.base_tab import BaseTab
from config.constants import PCS_DEFAULT_LEVELS
from config.settings_manager import get_settings_manager
from utils.logger import get_logger

logger = get_logger(__name__)


class ExitTab(BaseTab):
    """청산 설정 탭(안정 구현)"""

    exit_condition_changed = pyqtSignal(str, bool)

    def __init__(self, parent=None, trading_engine=None):
        self.trading_engine = trading_engine
        self.pcs_checkboxes: List[QCheckBox] = []
        self.pcs_table: QTableWidget | None = None
        super().__init__("청산 설정", parent)

        # 주기적 모니터링(필요 시 확장)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_monitoring_data)
        self.update_timer.start(1000)

    def init_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(12)

        # 1️⃣ PCS 청산 (12단계 + 1STEP/2STEP)
        pcs_group = self.create_pcs_section()
        container_layout.addWidget(pcs_group)

        # 2️⃣ PC 트레일링(PCT) 청산
        pct_group = self.create_pct_section()
        container_layout.addWidget(pct_group)

        # 3️⃣ 호가 청산
        bid_group = self.create_bid_exit_section()
        container_layout.addWidget(bid_group)

        # 4️⃣ PC 본절 청산
        pc_main_group = self.create_pc_main_exit_section()
        container_layout.addWidget(pc_main_group)

        # 📊 실시간 상태 표시
        status_group = self.create_status_section()
        container_layout.addWidget(status_group)

        # 이벤트 연결
        self.connect_signals()
        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def create_pcs_section(self) -> QGroupBox:
        """1️⃣ PCS 청산 (12단계 + 1STEP/2STEP) 섹션 생성"""
        group = QGroupBox("🎯 1. PCS 청산 (Price Channel System)")
        layout = QVBoxLayout(group)

        # 활성화 헤더
        header = QHBoxLayout()
        self.pcs_enabled = QCheckBox("PCS 청산 활성화")
        self.pcs_enabled.setChecked(True)
        header.addWidget(self.pcs_enabled)
        header.addStretch()
        layout.addLayout(header)

        # 12단계 선택 체크박스
        steps_layout = QGridLayout()
        steps_layout.addWidget(QLabel("활성화할 단계 선택:"), 0, 0, 1, 6)

        self.pcs_step_checkboxes = []
        for i in range(12):
            step = i + 1
            checkbox = QCheckBox(f"{step}단")
            if step <= 6:  # 기본적으로 1~6단 활성화
                checkbox.setChecked(True)
            self.pcs_step_checkboxes.append(checkbox)

            row = 1 + (i // 6)
            col = i % 6
            steps_layout.addWidget(checkbox, row, col)

        layout.addLayout(steps_layout)

        # STEP 방식 선택
        step_mode_layout = QGridLayout()
        step_mode_layout.addWidget(QLabel("STEP 방식 설정:"), 0, 0, 1, 4)

        self.pcs_step_modes = []
        for i in range(12):
            step = i + 1
            combo = QComboBox()
            combo.addItems(["1STEP (즉시 100%)", "2STEP (50% + 50%)"])
            if step <= 3:  # 1~3단은 1STEP
                combo.setCurrentIndex(0)
            else:  # 4~12단은 2STEP
                combo.setCurrentIndex(1)
            self.pcs_step_modes.append(combo)

            row = 1 + (i // 4)
            col = i % 4
            step_mode_layout.addWidget(QLabel(f"{step}단:"), row*2, col)
            step_mode_layout.addWidget(combo, row*2+1, col)

        layout.addLayout(step_mode_layout)

        # PCS 상태 테이블
        self.pcs_table = QTableWidget(12, 6)
        self.pcs_table.setHorizontalHeaderLabels(["단계", "활성화", "STEP방식", "상단선", "하단선", "상태"])
        for i, w in enumerate([40, 60, 100, 80, 80, 80]):
            self.pcs_table.setColumnWidth(i, w)
        self.pcs_table.setFixedHeight(320)
        self.pcs_table.verticalHeader().setVisible(False)
        self.pcs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.pcs_table)

        self.populate_pcs_table()
        return group

    def create_pct_section(self) -> QGroupBox:
        """2️⃣ PC 트레일링(PCT) 청산 섹션 생성"""
        group = QGroupBox("⚡ 2. PC 트레일링(PCT) 청산 (최종 안전장치)")
        layout = QVBoxLayout(group)

        # 활성화
        header = QHBoxLayout()
        self.pct_enabled = QCheckBox("PCT 청산 활성화")
        header.addWidget(self.pct_enabled)
        header.addStretch()
        layout.addLayout(header)

        # 손실중 청산 옵션
        options_layout = QGridLayout()
        options_layout.addWidget(QLabel("손실중 청산 옵션:"), 0, 0)

        self.pct_loss_only = QCheckBox("손실중에만 청산")
        self.pct_loss_only.setChecked(True)
        options_layout.addWidget(self.pct_loss_only, 0, 1)

        self.pct_always = QCheckBox("손실중/수익중 상관없이 청산")
        options_layout.addWidget(self.pct_always, 0, 2)

        layout.addLayout(options_layout)

        # 현재 상태
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("현재 상태:"))
        self.pct_status = QLabel("대기중 (PC선 변화 감시)")
        self.pct_status.setStyleSheet("color: orange; font-weight: bold;")
        status_layout.addWidget(self.pct_status)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        return group

    def create_bid_exit_section(self) -> QGroupBox:
        """3️⃣ 호가 청산 섹션 생성"""
        group = QGroupBox("🚨 3. 호가 청산 (빠른 대응)")
        layout = QVBoxLayout(group)

        # 매수 포지션 호가 청산
        long_layout = QGridLayout()
        long_layout.addWidget(QLabel("매수 포지션:"), 0, 0)

        self.bid_long_enabled = QCheckBox("하락 틱 청산 활성화")
        long_layout.addWidget(self.bid_long_enabled, 0, 1)

        self.bid_long_ticks = QSpinBox()
        self.bid_long_ticks.setRange(1, 100)
        self.bid_long_ticks.setValue(5)
        self.bid_long_ticks.setSuffix("틱")
        long_layout.addWidget(self.bid_long_ticks, 0, 2)

        long_layout.addWidget(QLabel("하락 시 청산"), 0, 3)
        layout.addLayout(long_layout)

        # 매도 포지션 호가 청산
        short_layout = QGridLayout()
        short_layout.addWidget(QLabel("매도 포지션:"), 0, 0)

        self.bid_short_enabled = QCheckBox("상승 틱 청산 활성화")
        short_layout.addWidget(self.bid_short_enabled, 0, 1)

        self.bid_short_ticks = QSpinBox()
        self.bid_short_ticks.setRange(1, 100)
        self.bid_short_ticks.setValue(3)
        self.bid_short_ticks.setSuffix("틱")
        short_layout.addWidget(self.bid_short_ticks, 0, 2)

        short_layout.addWidget(QLabel("상승 시 청산"), 0, 3)
        layout.addLayout(short_layout)

        # 현재 상태
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("현재 상태:"))
        self.bid_status = QLabel("대기중 (불리한 틱 움직임 감시)")
        self.bid_status.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(self.bid_status)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        return group

    def create_pc_main_exit_section(self) -> QGroupBox:
        """4️⃣ PC 본절 청산 (2단계 시스템) 섹션 생성"""
        group = QGroupBox("🔄 4. PC 본절 청산 (PC선 터치 후 틱 이동 청산)")
        layout = QVBoxLayout(group)

        # 활성화
        header = QHBoxLayout()
        self.pc_main_enabled = QCheckBox("PC 본절 청산 활성화")
        header.addWidget(self.pc_main_enabled)
        header.addStretch()
        layout.addLayout(header)

        # 틱 설정 섹션
        tick_section = QGroupBox("틱 설정")
        tick_layout = QGridLayout(tick_section)

        # 매수 포지션 틱 설정
        tick_layout.addWidget(QLabel("매수 포지션:"), 0, 0)
        tick_layout.addWidget(QLabel("하단선 터치 후"), 0, 1)
        self.pc_main_long_ticks = QSpinBox()
        self.pc_main_long_ticks.setRange(1, 100)
        self.pc_main_long_ticks.setValue(10)
        self.pc_main_long_ticks.setSuffix("틱")
        tick_layout.addWidget(self.pc_main_long_ticks, 0, 2)
        tick_layout.addWidget(QLabel("추가 하락 시 청산"), 0, 3)

        # 매도 포지션 틱 설정
        tick_layout.addWidget(QLabel("매도 포지션:"), 1, 0)
        tick_layout.addWidget(QLabel("상단선 터치 후"), 1, 1)
        self.pc_main_short_ticks = QSpinBox()
        self.pc_main_short_ticks.setRange(1, 100)
        self.pc_main_short_ticks.setValue(10)
        self.pc_main_short_ticks.setSuffix("틱")
        tick_layout.addWidget(self.pc_main_short_ticks, 1, 2)
        tick_layout.addWidget(QLabel("추가 상승 시 청산"), 1, 3)

        layout.addWidget(tick_section)

        # 매수 포지션 2단계
        long_group = QGroupBox("매수 포지션 상태")
        long_layout = QGridLayout(long_group)

        long_layout.addWidget(QLabel("1단계:"), 0, 0)
        self.pc_main_long_step1 = QLabel("PC 하단선 터치 대기중 ⏳")
        self.pc_main_long_step1.setStyleSheet("color: orange;")
        long_layout.addWidget(self.pc_main_long_step1, 0, 1)

        long_layout.addWidget(QLabel("2단계:"), 1, 0)
        self.pc_main_long_step2 = QLabel("비활성화 (하단선 미터치)")
        self.pc_main_long_step2.setStyleSheet("color: gray;")
        long_layout.addWidget(self.pc_main_long_step2, 1, 1)

        layout.addWidget(long_group)

        # 매도 포지션 2단계
        short_group = QGroupBox("매도 포지션 상태")
        short_layout = QGridLayout(short_group)

        short_layout.addWidget(QLabel("1단계:"), 0, 0)
        self.pc_main_short_step1 = QLabel("PC 상단선 터치 대기중 ⏳")
        self.pc_main_short_step1.setStyleSheet("color: orange;")
        short_layout.addWidget(self.pc_main_short_step1, 0, 1)

        short_layout.addWidget(QLabel("2단계:"), 1, 0)
        self.pc_main_short_step2 = QLabel("비활성화 (상단선 미터치)")
        self.pc_main_short_step2.setStyleSheet("color: gray;")
        short_layout.addWidget(self.pc_main_short_step2, 1, 1)

        layout.addWidget(short_group)

        return group

    def create_status_section(self) -> QGroupBox:
        """📊 실시간 상태 표시 섹션 생성"""
        group = QGroupBox("📊 실시간 청산 상태")
        layout = QGridLayout(group)

        # 현재 포지션 정보
        layout.addWidget(QLabel("현재 포지션:"), 0, 0)
        self.current_position = QLabel("포지션 없음")
        self.current_position.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.current_position, 0, 1)

        layout.addWidget(QLabel("진입가:"), 0, 2)
        self.entry_price = QLabel("$0")
        layout.addWidget(self.entry_price, 0, 3)

        layout.addWidget(QLabel("현재가:"), 1, 0)
        self.current_price = QLabel("$0")
        layout.addWidget(self.current_price, 1, 1)

        layout.addWidget(QLabel("수익률:"), 1, 2)
        self.profit_rate = QLabel("0.0%")
        layout.addWidget(self.profit_rate, 1, 3)

        # 활성화된 청산조건
        layout.addWidget(QLabel("활성화된 청산조건:"), 2, 0)
        self.active_conditions = QLabel("0개/4개")
        self.active_conditions.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(self.active_conditions, 2, 1)

        layout.addWidget(QLabel("청산 대기 상태:"), 2, 2)
        self.exit_waiting = QLabel("대기중")
        self.exit_waiting.setStyleSheet("color: green;")
        layout.addWidget(self.exit_waiting, 2, 3)

        return group

    def populate_pcs_table(self) -> None:
        """PCS 테이블을 새로운 형식으로 채우기"""
        try:
            # 기본적으로 1~6단 활성화
            enabled_steps = set(range(1, 7))
        except Exception:
            enabled_steps = set(range(1, 7))

        for row in range(12):
            step = row + 1
            active = step in enabled_steps

            # 단계
            self.pcs_table.setItem(row, 0, QTableWidgetItem(f"{step}단"))

            # 활성화
            active_item = QTableWidgetItem("✓" if active else "")
            active_item.setTextAlignment(Qt.AlignCenter)
            if active:
                active_item.setForeground(QColor("#28a745"))
            self.pcs_table.setItem(row, 1, active_item)

            # STEP 방식
            step_mode = "1STEP" if step <= 3 else "2STEP"
            step_item = QTableWidgetItem(step_mode)
            step_item.setTextAlignment(Qt.AlignCenter)
            step_item.setForeground(QColor("#007bff"))
            self.pcs_table.setItem(row, 2, step_item)

            # 상단선 (가상의 PC 상단선 값)
            upper_line = f"${50000 + step * 100:.0f}"
            upper_item = QTableWidgetItem(upper_line)
            upper_item.setTextAlignment(Qt.AlignCenter)
            upper_item.setForeground(QColor("#28a745"))
            self.pcs_table.setItem(row, 3, upper_item)

            # 하단선 (가상의 PC 하단선 값)
            lower_line = f"${49000 - step * 100:.0f}"
            lower_item = QTableWidgetItem(lower_line)
            lower_item.setTextAlignment(Qt.AlignCenter)
            lower_item.setForeground(QColor("#dc3545"))
            self.pcs_table.setItem(row, 4, lower_item)

            # 상태
            status = "모니터링" if active else "대기중"
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            if status == "모니터링":
                status_item.setBackground(QColor(255, 248, 220))
                status_item.setForeground(QColor(255, 140, 0))
            else:
                status_item.setBackground(QColor(248, 248, 255))
                status_item.setForeground(QColor(105, 105, 105))
            self.pcs_table.setItem(row, 5, status_item)

            self.pcs_table.setRowHeight(row, 28)

        self.pcs_table.repaint()

    def connect_signals(self):
        """PRD 기준 4가지 청산조건 시그널 연결"""
        # 1️⃣ PCS 청산 시그널
        if hasattr(self, 'pcs_enabled'):
            self.pcs_enabled.stateChanged.connect(self.on_exit_condition_changed)

        # PCS 단계별 체크박스
        if hasattr(self, 'pcs_step_checkboxes'):
            for checkbox in self.pcs_step_checkboxes:
                checkbox.stateChanged.connect(self.on_pcs_step_changed)

        # PCS STEP 모드 콤보박스
        if hasattr(self, 'pcs_step_modes'):
            for combo in self.pcs_step_modes:
                combo.currentTextChanged.connect(self.on_pcs_mode_changed)

        # 2️⃣ PC 트레일링(PCT) 청산 시그널
        if hasattr(self, 'pct_enabled'):
            self.pct_enabled.stateChanged.connect(self.on_exit_condition_changed)
        if hasattr(self, 'pct_loss_only'):
            self.pct_loss_only.stateChanged.connect(self.on_pct_option_changed)
        if hasattr(self, 'pct_always'):
            self.pct_always.stateChanged.connect(self.on_pct_option_changed)

        # 3️⃣ 호가 청산 시그널
        if hasattr(self, 'bid_long_enabled'):
            self.bid_long_enabled.stateChanged.connect(self.on_exit_condition_changed)
            self.bid_long_ticks.valueChanged.connect(self.on_exit_condition_changed)
        if hasattr(self, 'bid_short_enabled'):
            self.bid_short_enabled.stateChanged.connect(self.on_exit_condition_changed)
            self.bid_short_ticks.valueChanged.connect(self.on_exit_condition_changed)

        # 4️⃣ PC 본절 청산 시그널
        if hasattr(self, 'pc_main_enabled'):
            self.pc_main_enabled.stateChanged.connect(self.on_exit_condition_changed)

    def on_exit_condition_changed(self, state):
        """청산 조건 변경 핸들러"""
        self.update_exit_conditions()
        self.update_status_display()

    def on_pcs_step_changed(self, state):
        """PCS 단계 체크박스 변경 핸들러"""
        self.populate_pcs_table()
        self.update_exit_conditions()

    def on_pcs_mode_changed(self, text):
        """PCS STEP 모드 변경 핸들러"""
        self.populate_pcs_table()
        self.update_exit_conditions()

    def on_pct_option_changed(self, state):
        """PCT 손실중 옵션 변경 핸들러"""
        if hasattr(self, 'pct_loss_only') and hasattr(self, 'pct_always'):
            # 상호 배타적 체크박스
            sender = self.sender()
            if sender == self.pct_loss_only and state:
                self.pct_always.setChecked(False)
            elif sender == self.pct_always and state:
                self.pct_loss_only.setChecked(False)
        self.update_exit_conditions()

    def update_exit_conditions(self):
        """PRD 기준 4가지 청산조건 업데이트"""
        if not self.trading_engine:
            return
        try:
            # 기존 청산 조건 모두 제거
            self.trading_engine.exit_conditions.clear()
            conditions = []

            # ExitConditionFactory import
            from conditions.exit_condition_factory import ExitConditionFactory

            # 1️⃣ PCS 청산
            if hasattr(self, 'pcs_enabled') and self.pcs_enabled.isChecked():
                # PCS 테이블에서 활성화된 단계 수집
                active_steps = []
                for row in range(12):
                    checkbox = self.pcs_table.cellWidget(row, 1)
                    if checkbox and checkbox.isChecked():
                        tp_item = self.pcs_table.item(row, 2)
                        sl_item = self.pcs_table.item(row, 3)
                        if tp_item and sl_item:
                            tp = float(tp_item.text().replace('%', ''))
                            sl = float(sl_item.text().replace('%', ''))
                            active_steps.append({"tp": tp, "sl": sl})

                if active_steps:
                    pcs_config = {
                        "type": "pcs_system",
                        "enabled": True,
                        "params": {
                            "steps": active_steps,
                            "active_step": 1
                        }
                    }
                    pcs_condition = ExitConditionFactory.create_condition(pcs_config)
                    self.trading_engine.add_exit_condition(pcs_condition)
                    conditions.append("PCS 청산")
                    self.exit_condition_changed.emit("PCS 청산", True)

            # 2️⃣ PC 트레일링(PCT) 청산
            if hasattr(self, 'pct_enabled') and self.pct_enabled.isChecked():
                # PCT 조건 구현
                from conditions.exit.pct_exit import PCTExitCondition
                pct_config = {
                    'channel_period': self.pct_period.value() if hasattr(self, 'pct_period') else 20,
                    'trailing_offset': self.pct_offset.value() if hasattr(self, 'pct_offset') else 2.0,
                    'activation_profit': self.pct_activation.value() if hasattr(self, 'pct_activation') else 2.0
                }
                pct_condition = PCTExitCondition("PCT Exit", pct_config)
                self.trading_engine.add_exit_condition(pct_condition)
                conditions.append("PC 트레일링 청산")
                self.exit_condition_changed.emit("PC 트레일링 청산", True)

            # 3️⃣ 호가 청산
            bid_active = False
            if hasattr(self, 'bid_long_enabled') and self.bid_long_enabled.isChecked():
                bid_active = True
            if hasattr(self, 'bid_short_enabled') and self.bid_short_enabled.isChecked():
                bid_active = True
            if bid_active:
                # 호가 청산 조건 구현
                from conditions.exit.orderbook_exit import OrderbookExitCondition
                orderbook_config = {
                    'imbalance_ratio': self.bid_imbalance.value() if hasattr(self, 'bid_imbalance') else 2.0,
                    'depth_levels': self.bid_depth.value() if hasattr(self, 'bid_depth') else 5,
                    'consecutive_signals': 3,
                    'long_exit_on_sell_pressure': hasattr(self, 'bid_long_enabled') and self.bid_long_enabled.isChecked(),
                    'short_exit_on_buy_pressure': hasattr(self, 'bid_short_enabled') and self.bid_short_enabled.isChecked()
                }
                orderbook_condition = OrderbookExitCondition("Orderbook Exit", orderbook_config)
                self.trading_engine.add_exit_condition(orderbook_condition)
                conditions.append("호가 청산")
                self.exit_condition_changed.emit("호가 청산", True)

            # 4️⃣ PC 본절 청산
            if hasattr(self, 'pc_main_enabled') and self.pc_main_enabled.isChecked():
                # PC 본절 청산 틱 값 가져오기
                long_ticks = self.pc_main_long_ticks.value() if hasattr(self, 'pc_main_long_ticks') else 10
                short_ticks = self.pc_main_short_ticks.value() if hasattr(self, 'pc_main_short_ticks') else 10

                pc_config = {
                    "type": "pc_breakeven",
                    "enabled": True,
                    "params": {
                        "long_ticks": long_ticks,
                        "short_ticks": short_ticks
                    }
                }
                pc_condition = ExitConditionFactory.create_condition(pc_config)
                self.trading_engine.add_exit_condition(pc_condition)
                conditions.append(f"PC 본절 청산 (L:{long_ticks}틱/S:{short_ticks}틱)")
                self.exit_condition_changed.emit("PC 본절 청산", True)

            logger.info(f"활성화된 청산조건: {', '.join(conditions)} ({len(conditions)}개/4개)")
            logger.info(f"Trading Engine 청산조건 수: {len(self.trading_engine.exit_conditions)}개")
        except Exception as e:
            logger.error(f"청산 조건 업데이트 실패: {e}")

    def update_status_display(self):
        """실시간 상태 표시 업데이트"""
        try:
            # 활성화된 조건 수 계산
            active_count = 0
            if hasattr(self, 'pcs_enabled') and self.pcs_enabled.isChecked():
                active_count += 1
            if hasattr(self, 'pct_enabled') and self.pct_enabled.isChecked():
                active_count += 1
            if ((hasattr(self, 'bid_long_enabled') and self.bid_long_enabled.isChecked()) or
                (hasattr(self, 'bid_short_enabled') and self.bid_short_enabled.isChecked())):
                active_count += 1
            if hasattr(self, 'pc_main_enabled') and self.pc_main_enabled.isChecked():
                active_count += 1

            # 상태 표시 업데이트
            if hasattr(self, 'active_conditions'):
                self.active_conditions.setText(f"{active_count}개/4개")
                if active_count == 0:
                    self.active_conditions.setStyleSheet("color: red; font-weight: bold;")
                elif active_count <= 2:
                    self.active_conditions.setStyleSheet("color: orange; font-weight: bold;")
                else:
                    self.active_conditions.setStyleSheet("color: green; font-weight: bold;")

            if hasattr(self, 'exit_waiting'):
                if active_count > 0:
                    self.exit_waiting.setText("활성 감시중")
                    self.exit_waiting.setStyleSheet("color: orange; font-weight: bold;")
                else:
                    self.exit_waiting.setText("비활성")
                    self.exit_waiting.setStyleSheet("color: gray;")

        except Exception as e:
            logger.error(f"상태 표시 업데이트 실패: {e}")

    def update_monitoring_data(self):
        pass

    def get_settings(self) -> Dict[str, Any]:
        """PRD 기준 4가지 청산조건 설정 저장"""
        settings = {}

        # 1️⃣ PCS 청산 설정
        if hasattr(self, 'pcs_enabled'):
            settings["pcs_enabled"] = bool(self.pcs_enabled.isChecked())

        # PCS 단계별 활성화 상태
        if hasattr(self, 'pcs_step_checkboxes'):
            pcs_steps = []
            for i, checkbox in enumerate(self.pcs_step_checkboxes):
                pcs_steps.append(checkbox.isChecked())
            settings["pcs_steps"] = pcs_steps

        # PCS STEP 모드
        if hasattr(self, 'pcs_step_modes'):
            pcs_modes = []
            for combo in self.pcs_step_modes:
                pcs_modes.append(combo.currentIndex())
            settings["pcs_modes"] = pcs_modes

        # 2️⃣ PC 트레일링(PCT) 청산 설정
        if hasattr(self, 'pct_enabled'):
            settings["pct_enabled"] = bool(self.pct_enabled.isChecked())
        if hasattr(self, 'pct_loss_only'):
            settings["pct_loss_only"] = bool(self.pct_loss_only.isChecked())
        if hasattr(self, 'pct_always'):
            settings["pct_always"] = bool(self.pct_always.isChecked())

        # 3️⃣ 호가 청산 설정
        if hasattr(self, 'bid_long_enabled'):
            settings["bid_long_enabled"] = bool(self.bid_long_enabled.isChecked())
            settings["bid_long_ticks"] = int(self.bid_long_ticks.value())
        if hasattr(self, 'bid_short_enabled'):
            settings["bid_short_enabled"] = bool(self.bid_short_enabled.isChecked())
            settings["bid_short_ticks"] = int(self.bid_short_ticks.value())

        # 4️⃣ PC 본절 청산 설정
        if hasattr(self, 'pc_main_enabled'):
            settings["pc_main_enabled"] = bool(self.pc_main_enabled.isChecked())

        return settings

    def load_settings(self, settings: Dict[str, Any]):
        """PRD 기준 4가지 청산조건 설정 로드"""
        try:
            # 1️⃣ PCS 청산 설정 로드
            if hasattr(self, 'pcs_enabled'):
                self.pcs_enabled.setChecked(bool(settings.get("pcs_enabled", True)))

            # PCS 단계별 활성화 상태 복원
            if hasattr(self, 'pcs_step_checkboxes'):
                pcs_steps = settings.get("pcs_steps", [True] * 6 + [False] * 6)  # 기본: 1~6단 활성화
                for i, checkbox in enumerate(self.pcs_step_checkboxes):
                    if i < len(pcs_steps):
                        checkbox.setChecked(pcs_steps[i])

            # PCS STEP 모드 복원
            if hasattr(self, 'pcs_step_modes'):
                pcs_modes = settings.get("pcs_modes", [0, 0, 0] + [1] * 9)  # 기본: 1~3단=1STEP, 4~12단=2STEP
                for i, combo in enumerate(self.pcs_step_modes):
                    if i < len(pcs_modes):
                        combo.setCurrentIndex(pcs_modes[i])

            # 2️⃣ PC 트레일링(PCT) 청산 설정 로드
            if hasattr(self, 'pct_enabled'):
                self.pct_enabled.setChecked(bool(settings.get("pct_enabled", False)))
            if hasattr(self, 'pct_loss_only'):
                self.pct_loss_only.setChecked(bool(settings.get("pct_loss_only", True)))
            if hasattr(self, 'pct_always'):
                self.pct_always.setChecked(bool(settings.get("pct_always", False)))

            # 3️⃣ 호가 청산 설정 로드
            if hasattr(self, 'bid_long_enabled'):
                self.bid_long_enabled.setChecked(bool(settings.get("bid_long_enabled", False)))
                self.bid_long_ticks.setValue(int(settings.get("bid_long_ticks", 5)))
            if hasattr(self, 'bid_short_enabled'):
                self.bid_short_enabled.setChecked(bool(settings.get("bid_short_enabled", False)))
                self.bid_short_ticks.setValue(int(settings.get("bid_short_ticks", 3)))

            # 4️⃣ PC 본절 청산 설정 로드
            if hasattr(self, 'pc_main_enabled'):
                self.pc_main_enabled.setChecked(bool(settings.get("pc_main_enabled", False)))

            # 설정 로드 후 테이블 및 상태 업데이트
            self.populate_pcs_table()
            self.update_status_display()

        except Exception as e:
            logger.error(f"PRD 청산 설정 로드 실패: {e}")

    # 누락된 위젯 별칭 및 메소드 추가
    @property
    def pct_checkbox(self):
        """PCT 체크박스 별칭"""
        return getattr(self, 'pct_enabled', None)

    @property
    def orderbook_checkbox(self):
        """호가 청산 체크박스 별칭"""
        return getattr(self, 'bid_long_enabled', None)

    @property
    def pct_period_input(self):
        """PCT 기간 입력 위젯 (임시)"""
        # 실제 PCT 기간 입력 위젯이 없으면 임시로 생성
        if not hasattr(self, '_pct_period_input'):
            from PyQt5.QtWidgets import QSpinBox
            self._pct_period_input = QSpinBox()
            self._pct_period_input.setRange(1, 100)
            self._pct_period_input.setValue(20)
        return self._pct_period_input

    @property
    def pct_offset_input(self):
        """PCT 오프셋 입력 위젯 (임시)"""
        if not hasattr(self, '_pct_offset_input'):
            from PyQt5.QtWidgets import QDoubleSpinBox
            self._pct_offset_input = QDoubleSpinBox()
            self._pct_offset_input.setRange(0.1, 10.0)
            self._pct_offset_input.setValue(2.0)
        return self._pct_offset_input

    @property
    def imbalance_ratio_input(self):
        """호가 불균형 비율 입력 위젯 (임시)"""
        if not hasattr(self, '_imbalance_ratio_input'):
            from PyQt5.QtWidgets import QDoubleSpinBox
            self._imbalance_ratio_input = QDoubleSpinBox()
            self._imbalance_ratio_input.setRange(1.0, 5.0)
            self._imbalance_ratio_input.setValue(2.0)
        return self._imbalance_ratio_input

    def update_pcs(self):
        """PCS 청산 조건 업데이트"""
        self.update_exit_conditions()

    def update_pct(self):
        """PCT 청산 조건 업데이트"""
        if self.trading_engine and hasattr(self, 'pct_enabled'):
            if self.pct_enabled.isChecked():
                # PCT 조건 추가
                from conditions.exit.pct_exit import PCTExitCondition
                config = {
                    'channel_period': self.pct_period_input.value() if hasattr(self, 'pct_period_input') else 20,
                    'trailing_offset': self.pct_offset_input.value() if hasattr(self, 'pct_offset_input') else 2.0,
                    'activation_profit': 2.0
                }
                pct_condition = PCTExitCondition("PCT Exit", config)
                self.trading_engine.add_exit_condition(pct_condition)

    def update_orderbook(self):
        """호가 청산 조건 업데이트"""
        if self.trading_engine and hasattr(self, 'bid_long_enabled'):
            if self.bid_long_enabled.isChecked() or (hasattr(self, 'bid_short_enabled') and self.bid_short_enabled.isChecked()):
                # 호가 청산 조건 추가
                from conditions.exit.orderbook_exit import OrderbookExitCondition
                config = {
                    'imbalance_ratio': self.imbalance_ratio_input.value() if hasattr(self, 'imbalance_ratio_input') else 2.0,
                    'depth_levels': 5,
                    'consecutive_signals': 3,
                    'long_exit_on_sell_pressure': getattr(self, 'bid_long_enabled', None) and self.bid_long_enabled.isChecked(),
                    'short_exit_on_buy_pressure': getattr(self, 'bid_short_enabled', None) and self.bid_short_enabled.isChecked()
                }
                orderbook_condition = OrderbookExitCondition("Orderbook Exit", config)
                self.trading_engine.add_exit_condition(orderbook_condition)

