"""
API 연결 테스트 다이얼로그

거래소 API 연결을 테스트하는 GUI 다이얼로그
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor

from api.base_api import APICredentials
from api.binance.futures_client import BinanceFuturesClient
from api.bybit.futures_client import BybitFuturesClient
from utils.logger import get_logger

logger = get_logger(__name__)


class APITestWorker(QThread):
    """API 테스트 작업 스레드"""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, exchange: str, api_key: str, secret_key: str, testnet: bool = True):
        super().__init__()
        self.exchange = exchange
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet

    def run(self):
        """API 테스트 실행"""
        try:
            self.log_signal.emit(f"[INFO] {self.exchange} API 연결 테스트 시작...")
            self.progress_signal.emit(10)

            # API 키 확인
            if not self.api_key or not self.secret_key:
                self.log_signal.emit("[ERROR] API 키가 설정되지 않았습니다.")
                self.finished_signal.emit(False, "API 키가 설정되지 않았습니다.")
                return

            # API 클라이언트 생성
            self.log_signal.emit(f"[INFO] API 클라이언트 생성 중...")
            self.progress_signal.emit(20)

            credentials = APICredentials(
                api_key=self.api_key,
                secret_key=self.secret_key,
                testnet=self.testnet
            )

            if self.exchange.lower() == "binance":
                client = BinanceFuturesClient(credentials)
            elif self.exchange.lower() == "bybit":
                client = BybitFuturesClient(credentials)
            else:
                self.log_signal.emit(f"[ERROR] 지원하지 않는 거래소: {self.exchange}")
                self.finished_signal.emit(False, "지원하지 않는 거래소")
                return

            self.log_signal.emit(f"[INFO] 엔드포인트: {'테스트넷' if self.testnet else '실거래'}")
            self.log_signal.emit(f"[INFO] Base URL: {client.base_url}")
            if self.testnet:
                self.log_signal.emit("[TIP] 테스트넷 모드: 주문은 샌드박스(endpoints)로 전송되며 실자산에 영향이 없습니다.")
            else:
                self.log_signal.emit("[WARN] 실거래 모드: 실제 주문이 전송될 수 있습니다. 포지션 크기와 API 권한을 확인하세요.")
            self.progress_signal.emit(30)

            # 1. 연결 테스트
            self.log_signal.emit("\n[1] 서버 연결 테스트 (ping)...")
            self.progress_signal.emit(40)

            if client.test_connectivity():
                self.log_signal.emit("    [OK] 서버 연결 성공")
            else:
                self.log_signal.emit("    [FAIL] 서버 연결 실패")
                self.finished_signal.emit(False, "서버 연결 실패")
                return

            # 2. 서버 시간 확인
            self.log_signal.emit("\n[2] 서버 시간 확인...")
            self.progress_signal.emit(50)

            try:
                server_time = client.get_server_time()
                if server_time:
                    from datetime import datetime
                    server_datetime = datetime.fromtimestamp(server_time / 1000)
                    self.log_signal.emit(f"    [OK] 서버 시간: {server_datetime}")
                else:
                    self.log_signal.emit("    [WARN] 서버 시간을 가져올 수 없습니다.")
            except Exception as e:
                self.log_signal.emit(f"    [ERROR] {str(e)}")

            # 3. 계정 정보 조회
            self.log_signal.emit("\n[3] 계정 정보 조회...")
            self.progress_signal.emit(70)

            try:
                account_info = client.get_account_info()
                if account_info:
                    # AccountInfo 객체의 올바른 속성 사용
                    self.log_signal.emit(f"    [OK] 총 잔고: {account_info.total_balance:.2f} USDT")
                    self.log_signal.emit(f"    [OK] 사용 가능: {account_info.available_balance:.2f} USDT")
                    self.log_signal.emit(f"    [OK] 미실현 손익: {account_info.unrealized_pnl:.2f} USDT")
                    self.log_signal.emit(f"    [OK] 사용 마진: {account_info.used_margin:.2f} USDT")

                    if account_info.positions:
                        self.log_signal.emit(f"    [OK] 활성 포지션: {len(account_info.positions)}개")
                else:
                    self.log_signal.emit("    [WARN] 계정 정보를 가져올 수 없습니다.")
            except Exception as e:
                self.log_signal.emit(f"    [ERROR] {str(e)}")
                self.log_signal.emit("    [TIP] API 키 권한을 확인하세요 (선물 거래 권한 필요)")

            # 4. 가격 조회
            self.log_signal.emit("\n[4] BTC 가격 조회...")
            self.progress_signal.emit(90)

            try:
                ticker = client.get_ticker("BTCUSDT")
                if ticker:
                    self.log_signal.emit(f"    [OK] BTC 현재가: ${ticker.price:,.2f}")
                    self.log_signal.emit(f"    [OK] 24시간 변동률: {ticker.change_percent_24h:.2f}%")
                else:
                    self.log_signal.emit("    [WARN] 가격 정보를 가져올 수 없습니다.")
            except Exception as e:
                self.log_signal.emit(f"    [ERROR] {str(e)}")

            # 완료
            self.progress_signal.emit(100)
            self.log_signal.emit("\n" + "="*50)
            self.log_signal.emit(f"[SUCCESS] {self.exchange} API 연결 테스트 완료!")
            self.finished_signal.emit(True, "API 연결 테스트 성공")

        except Exception as e:
            logger.error(f"API 테스트 중 오류: {e}")
            self.log_signal.emit(f"\n[ERROR] 테스트 중 오류 발생: {str(e)}")
            self.finished_signal.emit(False, str(e))


class APITestDialog(QDialog):
    """API 연결 테스트 다이얼로그"""

    def __init__(self, parent=None, exchange="Binance", api_key="", secret_key="", testnet=True):
        super().__init__(parent)
        self.exchange = exchange
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        self.worker = None

        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle(f"{self.exchange} API 연결 테스트")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()

        # 헤더
        header_group = QGroupBox("API 연결 정보")
        header_layout = QVBoxLayout(header_group)

        info_text = f"""
        거래소: {self.exchange}
        엔드포인트: {'테스트넷' if self.testnet else '실거래'}
        API 키: {self.api_key[:20]}... (마스킹)
        """

        info_label = QLabel(info_text)
        info_label.setStyleSheet("font-family: monospace; padding: 10px;")
        header_layout.addWidget(info_label)

        layout.addWidget(header_group)

        # 로그 출력 영역
        log_group = QGroupBox("테스트 로그")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #444;
            }
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        # 진행 상태바
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #444;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #05B8CC;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 버튼
        button_layout = QHBoxLayout()

        self.test_btn = QPushButton("테스트 시작")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.test_btn.clicked.connect(self.start_test)
        button_layout.addWidget(self.test_btn)

        self.close_btn = QPushButton("닫기")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def start_test(self):
        """테스트 시작"""
        self.test_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_text.clear()

        # 워커 스레드 생성 및 시작
        self.worker = APITestWorker(
            self.exchange,
            self.api_key,
            self.secret_key,
            self.testnet
        )

        # 시그널 연결
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.test_finished)

        # 테스트 시작
        self.worker.start()

    def append_log(self, message):
        """로그 메시지 추가"""
        # 색상 코드 적용
        if "[OK]" in message or "[SUCCESS]" in message:
            color = "#4EC9B0"  # 녹색
        elif "[ERROR]" in message or "[FAIL]" in message:
            color = "#F48771"  # 빨간색
        elif "[WARN]" in message:
            color = "#DCDCAA"  # 노란색
        elif "[INFO]" in message:
            color = "#9CDCFE"  # 파란색
        elif "[TIP]" in message:
            color = "#C586C0"  # 보라색
        else:
            color = "#d4d4d4"  # 기본 색상

        # HTML 형식으로 색상 적용
        html_message = f'<span style="color: {color};">{message}</span>'

        # 텍스트 추가
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertHtml(html_message + "<br>")

        # 자동 스크롤
        self.log_text.ensureCursorVisible()

    def update_progress(self, value):
        """진행률 업데이트"""
        self.progress_bar.setValue(value)

    def test_finished(self, success, message):
        """테스트 완료"""
        self.test_btn.setEnabled(True)

        if success:
            self.append_log("\n테스트가 성공적으로 완료되었습니다!")
        else:
            self.append_log(f"\n테스트 실패: {message}")
