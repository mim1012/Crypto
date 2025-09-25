"""
시간 제어 탭 모듈 - 완전 복원 버전

이 모듈은 거래 시간 제어 설정 UI를 구현합니다.
원본 GUI의 모든 기능을 모듈화된 구조로 완전 복원했습니다.
"""

from typing import Dict, Any, List
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, 
    QCheckBox, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QFrame, QTabWidget, QWidget,
    QScrollArea, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QDateTime
from PyQt5.QtGui import QFont

from gui.base_tab import BaseTab
from utils.logger import get_logger

logger = get_logger(__name__)


class TimeTab(BaseTab):
    """시간 제어 탭 - 완전 복원"""
    
    # 시간 제어 관련 시그널
    time_control_changed = pyqtSignal(str, bool)
    trading_time_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None, trading_engine=None):
        super().__init__("시간 제어", parent)

        self.trading_engine = trading_engine
        # 시간 제어 상태
        self.time_controls = {}
        self.weekday_controls = {}
        
        # 현재 시간 정보
        self.current_time = QDateTime.currentDateTime()
        self.current_status = "대기중"
        self.current_weekday = "토요일"
    
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
        
        # 1. 현재 상태
        self.create_current_status(scroll_layout)
        
        # 2. 요일별 거래시간 설정
        self.create_weekday_settings(scroll_layout)
        
        # 3. 24시간 가동 및 휴일 제외
        self.create_additional_settings(scroll_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
        
        # 실시간 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_current_time)
        self.update_timer.start(1000)  # 1초마다 업데이트

        # 시그널 연결
        self.connect_time_signals()
    
    def create_current_status(self, layout):
        """현재 상태 표시"""
        group = QGroupBox("📊 현재 상태")
        group_layout = QVBoxLayout(group)
        
        # 현재 시간 정보
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("상태: 대기중")
        self.current_weekday_label = QLabel("요일: 토요일")
        self.current_clock_label = QLabel("시간: 14:38:07")
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.current_weekday_label)
        time_layout.addStretch()
        time_layout.addWidget(self.current_clock_label)
        
        group_layout.addLayout(time_layout)
        
        # 거래 가능 시간 정보
        trading_info_frame = QFrame()
        trading_info_frame.setFrameStyle(QFrame.Box)
        trading_info_frame.setStyleSheet("background-color: #e8f5e8; border: 2px solid #28a745; padding: 8px;")
        trading_info_layout = QHBoxLayout(trading_info_frame)
        
        self.trading_status_label = QLabel("🕐 거래 시간: 평일 09:00 ~ 15:30")
        self.next_trading_label = QLabel("다음 거래: 월요일 09:00")
        
        trading_info_layout.addWidget(self.trading_status_label)
        trading_info_layout.addStretch()
        trading_info_layout.addWidget(self.next_trading_label)
        
        group_layout.addWidget(trading_info_frame)
        layout.addWidget(group)
    
    def create_weekday_settings(self, layout):
        """요일별 거래시간 설정"""
        group = QGroupBox("🗓️ 요일별 거래시간 설정")
        group_layout = QVBoxLayout(group)
        
        # 요일별 설정
        weekdays = [
            ("월요일", True, True, False),
            ("화요일", True, True, False), 
            ("수요일", True, True, False),
            ("목요일", True, True, False),
            ("금요일", True, True, False),
            ("토요일", False, False, False),
            ("일요일", False, False, False)
        ]
        
        self.weekday_widgets = {}
        
        for day_name, active_default, second_default, force_default in weekdays:
            day_frame = QFrame()
            day_frame.setFrameStyle(QFrame.Box)
            day_frame.setStyleSheet("border: 1px solid #dee2e6; padding: 5px; margin: 2px;")
            day_layout = QGridLayout(day_frame)
            
            # 요일 라벨
            day_label = QLabel(day_name)
            day_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
            day_layout.addWidget(day_label, 0, 0)
            
            # 활성화 체크박스
            active_check = QCheckBox("활성화")
            active_check.setChecked(active_default)
            active_check.setStyleSheet("color: #28a745; font-weight: bold;")
            day_layout.addWidget(active_check, 0, 1)
            
            # 2차 체크박스
            second_check = QCheckBox("2차")
            second_check.setChecked(second_default)
            second_check.setStyleSheet("color: #007bff; font-weight: bold;")
            day_layout.addWidget(second_check, 0, 2)
            
            # 강제청산 체크박스
            force_check = QCheckBox("강제청산")
            force_check.setChecked(force_default)
            force_check.setStyleSheet("color: #dc3545; font-weight: bold;")
            day_layout.addWidget(force_check, 0, 3)
            
            # 1차 시간 설정
            day_layout.addWidget(QLabel("1차:"), 0, 4)
            
            start_time1 = QComboBox()
            start_time1.addItems(self.generate_time_options())
            start_time1.setCurrentText("오전 9:00")
            day_layout.addWidget(start_time1, 0, 5)
            
            day_layout.addWidget(QLabel("~"), 0, 6)
            
            end_time1 = QComboBox()
            end_time1.addItems(self.generate_time_options())
            end_time1.setCurrentText("오전 12:00")
            day_layout.addWidget(end_time1, 0, 7)
            
            # 2차 시간 설정
            day_layout.addWidget(QLabel("2차:"), 0, 8)
            
            start_time2 = QComboBox()
            start_time2.addItems(self.generate_time_options())
            start_time2.setCurrentText("오후 1:00")
            day_layout.addWidget(start_time2, 0, 9)
            
            day_layout.addWidget(QLabel("~"), 0, 10)
            
            end_time2 = QComboBox()
            end_time2.addItems(self.generate_time_options())
            end_time2.setCurrentText("오후 3:30")
            day_layout.addWidget(end_time2, 0, 11)
            
            # 강제청산 시간
            day_layout.addWidget(QLabel("강제청산:"), 0, 12)
            
            force_time = QComboBox()
            force_time.addItems(self.generate_time_options())
            force_time.setCurrentText("오후 6:00")
            day_layout.addWidget(force_time, 0, 13)
            
            # 위젯 저장
            self.weekday_widgets[day_name] = {
                'active': active_check,
                'second': second_check,
                'force': force_check,
                'start_time1': start_time1,
                'end_time1': end_time1,
                'start_time2': start_time2,
                'end_time2': end_time2,
                'force_time': force_time
            }
            
            group_layout.addWidget(day_frame)
        
        layout.addWidget(group)
    
    def create_additional_settings(self, layout):
        """추가 설정"""
        group = QGroupBox("⚙️ 추가 설정")
        group_layout = QVBoxLayout(group)
        
        # 24시간 가동
        self.full_time_check = QCheckBox("24시간 가동")
        self.full_time_check.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 11pt;")
        group_layout.addWidget(self.full_time_check)
        
        # 영업시간 가동
        self.business_hours_check = QCheckBox("영업시간 가동")
        self.business_hours_check.setChecked(True)
        self.business_hours_check.setStyleSheet("color: #28a745; font-weight: bold; font-size: 11pt;")
        group_layout.addWidget(self.business_hours_check)
        
        # 휴일 제외
        self.exclude_holidays_check = QCheckBox("휴일 제외")
        self.exclude_holidays_check.setChecked(True)
        self.exclude_holidays_check.setStyleSheet("color: #6f42c1; font-weight: bold; font-size: 11pt;")
        group_layout.addWidget(self.exclude_holidays_check)
        
        # 상태 메시지
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Box)
        status_frame.setStyleSheet("background-color: #fff3cd; border: 2px solid #ffc107; padding: 8px;")
        status_layout = QHBoxLayout(status_frame)
        
        self.time_status_message = QLabel("⚠️ 현재 시간: 거래 시간 외 (토요일)")
        self.time_status_message.setStyleSheet("color: #856404; font-weight: bold;")
        status_layout.addWidget(self.time_status_message)
        
        group_layout.addWidget(status_frame)
        layout.addWidget(group)
    
    def generate_time_options(self):
        """시간 옵션 생성 (30분 단위)"""
        times = []
        for hour in range(24):
            for minute in [0, 30]:
                if hour < 12:
                    period = "오전"
                    display_hour = hour if hour != 0 else 12
                else:
                    period = "오후"
                    display_hour = hour if hour == 12 else hour - 12
                
                time_str = f"{period} {display_hour}:{minute:02d}"
                times.append(time_str)
        return times
    
    def update_current_time(self):
        """현재 시간 업데이트"""
        try:
            self.current_time = QDateTime.currentDateTime()
            
            # 현재 시간 표시
            current_time_str = self.current_time.toString("hh:mm:ss")
            self.current_clock_label.setText(f"시간: {current_time_str}")
            
            # 요일 표시
            weekday_names = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"]
            current_weekday = weekday_names[self.current_time.date().dayOfWeek() % 7]
            self.current_weekday_label.setText(f"요일: {current_weekday}")
            
            # 거래 상태 업데이트
            self.update_trading_status(current_weekday)
            
        except Exception as e:
            logger.error(f"시간 업데이트 오류: {e}")
    
    def update_trading_status(self, current_weekday):
        """거래 상태 업데이트"""
        try:
            # 24시간 가동 체크
            if self.full_time_check.isChecked():
                self.current_time_label.setText("상태: 24시간 가동 중")
                self.time_status_message.setText("✅ 24시간 가동 모드 활성화")
                return
            
            # 요일별 거래 시간 체크
            if current_weekday in self.weekday_widgets:
                weekday_setting = self.weekday_widgets[current_weekday]
                
                if weekday_setting['active'].isChecked():
                    self.current_time_label.setText("상태: 거래 가능")
                    self.time_status_message.setText(f"✅ {current_weekday} 거래 시간")
                else:
                    self.current_time_label.setText("상태: 거래 불가")
                    self.time_status_message.setText(f"⚠️ {current_weekday} 거래 시간 외")
            else:
                self.current_time_label.setText("상태: 대기중")
                self.time_status_message.setText("⏳ 거래 시간 확인 중")
            
        except Exception as e:
            logger.error(f"거래 상태 업데이트 오류: {e}")
    
    def get_settings(self) -> Dict[str, Any]:
        """현재 설정값 반환"""
        weekday_settings = {}
        for day_name, widgets in self.weekday_widgets.items():
            weekday_settings[day_name] = {
                'active': widgets['active'].isChecked(),
                'second': widgets['second'].isChecked(),
                'force': widgets['force'].isChecked(),
                'start_time1': widgets['start_time1'].currentText(),
                'end_time1': widgets['end_time1'].currentText(),
                'start_time2': widgets['start_time2'].currentText(),
                'end_time2': widgets['end_time2'].currentText(),
                'force_time': widgets['force_time'].currentText()
            }
        
        return {
            'weekday_settings': weekday_settings,
            'additional_settings': {
                'full_time': self.full_time_check.isChecked(),
                'business_hours': self.business_hours_check.isChecked(),
                'exclude_holidays': self.exclude_holidays_check.isChecked()
            }
        }
    
    def load_settings(self, settings: Dict[str, Any]):
        """설정값 로드"""
        try:
            # 요일별 설정 로드
            weekday_settings = settings.get('weekday_settings', {})
            for day_name, day_settings in weekday_settings.items():
                if day_name in self.weekday_widgets:
                    widgets = self.weekday_widgets[day_name]
                    widgets['active'].setChecked(day_settings.get('active', False))
                    widgets['second'].setChecked(day_settings.get('second', False))
                    widgets['force'].setChecked(day_settings.get('force', False))
                    
                    if 'start_time1' in day_settings:
                        widgets['start_time1'].setCurrentText(day_settings['start_time1'])
                    if 'end_time1' in day_settings:
                        widgets['end_time1'].setCurrentText(day_settings['end_time1'])
                    if 'start_time2' in day_settings:
                        widgets['start_time2'].setCurrentText(day_settings['start_time2'])
                    if 'end_time2' in day_settings:
                        widgets['end_time2'].setCurrentText(day_settings['end_time2'])
                    if 'force_time' in day_settings:
                        widgets['force_time'].setCurrentText(day_settings['force_time'])
            
            # 추가 설정 로드
            additional_settings = settings.get('additional_settings', {})
            self.full_time_check.setChecked(additional_settings.get('full_time', False))
            self.business_hours_check.setChecked(additional_settings.get('business_hours', True))
            self.exclude_holidays_check.setChecked(additional_settings.get('exclude_holidays', True))
            
            logger.info("시간 제어 탭 설정값 로드 완료")

        except Exception as e:
            logger.error(f"설정값 로드 오류: {e}")

    def connect_time_signals(self):
        """시간 제어 시그널 연결"""
        # 24시간 가동 / 영업시간 가동
        self.full_time_check.stateChanged.connect(self.update_time_controls)
        self.business_hours_check.stateChanged.connect(self.update_time_controls)
        self.exclude_holidays_check.stateChanged.connect(self.update_time_controls)

        # 요일별 설정
        for day_name, widgets in self.weekday_widgets.items():
            widgets['active'].stateChanged.connect(self.update_time_controls)
            widgets['second'].stateChanged.connect(self.update_time_controls)
            widgets['force'].stateChanged.connect(self.update_time_controls)
            widgets['start_time1'].currentTextChanged.connect(self.update_time_controls)
            widgets['end_time1'].currentTextChanged.connect(self.update_time_controls)
            widgets['start_time2'].currentTextChanged.connect(self.update_time_controls)
            widgets['end_time2'].currentTextChanged.connect(self.update_time_controls)
            widgets['force_time'].currentTextChanged.connect(self.update_time_controls)

    def update_time_controls(self):
        """시간 제어 설정 업데이트"""
        if not self.trading_engine:
            logger.debug("거래 엔진이 설정되지 않았습니다")
            return

        try:
            # 시간 제어 설정 수집
            time_config = {
                "full_time": self.full_time_check.isChecked(),
                "business_hours": self.business_hours_check.isChecked(),
                "exclude_holidays": self.exclude_holidays_check.isChecked(),
                "weekday_settings": {}
            }

            # 요일별 설정 수집
            for day_name, widgets in self.weekday_widgets.items():
                time_config["weekday_settings"][day_name] = {
                    "active": widgets['active'].isChecked(),
                    "second_session": widgets['second'].isChecked(),
                    "force_exit": widgets['force'].isChecked(),
                    "start_time1": widgets['start_time1'].currentText(),
                    "end_time1": widgets['end_time1'].currentText(),
                    "start_time2": widgets['start_time2'].currentText(),
                    "end_time2": widgets['end_time2'].currentText(),
                    "force_exit_time": widgets['force_time'].currentText()
                }

            # 거래 엔진에 시간 제어 설정 적용
            if hasattr(self.trading_engine, 'set_time_control'):
                self.trading_engine.set_time_control(time_config)

            # 시간 제어 변경 시그널 발송
            self.time_control_changed.emit(
                "시간 제어 설정",
                True
            )

            logger.info("시간 제어 설정 업데이트 완료")

        except Exception as e:
            logger.error(f"시간 제어 설정 업데이트 실패: {e}")
