"""
GUI 탭 기본 클래스

이 모듈은 모든 GUI 탭의 기본 인터페이스를 정의합니다.
"""

from typing import Dict, Any, Optional, List
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from utils.logger import get_logger

logger = get_logger(__name__)


class BaseTab(QWidget):
    """GUI 탭 기본 클래스"""
    
    # 시그널 정의
    settings_changed = pyqtSignal(dict)  # 설정 변경 시그널
    action_requested = pyqtSignal(str, dict)  # 액션 요청 시그널
    status_updated = pyqtSignal(str, str)  # 상태 업데이트 시그널
    
    def __init__(self, tab_name: str, parent=None):
        super().__init__(parent)
        
        self.tab_name = tab_name
        self.settings = {}
        self.is_initialized = False
        
        logger.info(f"{self.tab_name} 탭 초기화 시작")

        # UI 초기화를 try-except로 감싸서 오류 처리
        try:
            self.init_ui()
            self.is_initialized = True
            logger.info(f"{self.tab_name} 탭 초기화 완료")
        except Exception as e:
            logger.error(f"{self.tab_name} 탭 초기화 중 오류: {e}")
            self.is_initialized = False
    
    def init_ui(self) -> None:
        """UI 초기화 (서브클래스에서 구현)"""
        pass
    
    def get_settings(self) -> Dict[str, Any]:
        """현재 설정 반환 (서브클래스에서 구현)"""
        return self.settings
    
    def load_settings(self, settings: Dict[str, Any]) -> None:
        """설정 로드 (서브클래스에서 구현)"""
        self.settings.update(settings)
    
    def create_frame_layout(self, layout):
        """프레임 레이아웃 생성 헬퍼"""
        from PyQt5.QtWidgets import QFrame
        frame = QFrame()
        frame.setLayout(layout)
        return frame
    
    def add_entry_separator(self, layout):
        """구분선 추가 헬퍼"""
        from PyQt5.QtWidgets import QFrame
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #dee2e6; margin: 5px 0;")
        layout.addWidget(separator)
