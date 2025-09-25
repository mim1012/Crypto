"""
시스템 상수 정의 모듈

이 모듈은 시스템 전반에서 사용되는 상수들을 정의합니다.
"""

# 거래소 관련 상수
SUPPORTED_EXCHANGES = ["binance", "bybit"]
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_LEVERAGE = 10
MAX_LEVERAGE = 125
MIN_LEVERAGE = 1

# 포지션 관리 상수
MAX_POSITIONS = 10
MIN_POSITIONS = 1
DEFAULT_POSITION_SIZE = 1000.0
MAX_POSITION_SIZE = 1000000.0
MIN_POSITION_SIZE = 10.0

# 리스크 관리 상수
MAX_RISK_PERCENTAGE = 10.0
MIN_RISK_PERCENTAGE = 0.1
DEFAULT_RISK_PERCENTAGE = 2.0
MAX_DAILY_LOSS_LIMIT = 20.0
DEFAULT_DAILY_LOSS_LIMIT = 5.0

# 진입 조건 상수
ENTRY_CONDITION_TYPES = [
    "moving_average",
    "price_channel", 
    "orderbook",
    "tick_based",
    "candle_state"
]

COMBINATION_MODES = ["AND", "OR"]

# 이동평균 조건 타입
MA_CONDITION_TYPES = [
    "close_above",
    "close_below", 
    "open_above",
    "open_below"
]

# Price Channel 조건 타입
PC_BREAKOUT_TYPES = [
    "upper_buy",
    "upper_sell",
    "lower_buy", 
    "lower_sell",
    "none"
]

# 신호 타입
SIGNAL_TYPES = ["BUY", "SELL"]
ORDER_TYPES = ["MARKET", "LIMIT", "STOP", "STOP_MARKET"]
ORDER_SIDES = ["BUY", "SELL"]

# 청산 조건 상수
PCS_STEPS = 12
EXIT_CONDITION_TYPES = [
    "pcs",
    "pc_trailing",
    "orderbook_exit", 
    "pc_breakout"
]

# 시간 제어 상수
WEEKDAYS = [
    "monday",
    "tuesday", 
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday"
]

TIME_INTERVALS = [
    "00:00", "00:30", "01:00", "01:30", "02:00", "02:30",
    "03:00", "03:30", "04:00", "04:30", "05:00", "05:30",
    "06:00", "06:30", "07:00", "07:30", "08:00", "08:30",
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
    "18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
    "21:00", "21:30", "22:00", "22:30", "23:00", "23:30"
]

# API 관련 상수
API_TIMEOUT = 30
WEBSOCKET_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 1.0

# 바이낸스 API 엔드포인트
BINANCE_BASE_URL = "https://fapi.binance.com"
BINANCE_TESTNET_URL = "https://testnet.binancefuture.com"
BINANCE_WS_URL = "wss://fstream.binance.com/ws/"
BINANCE_TESTNET_WS_URL = "wss://stream.binancefuture.com/ws/"

# 바이비트 API 엔드포인트  
BYBIT_BASE_URL = "https://api.bybit.com"
BYBIT_TESTNET_URL = "https://api-testnet.bybit.com"
BYBIT_WS_URL = "wss://stream.bybit.com/v5/public/linear"
BYBIT_TESTNET_WS_URL = "wss://stream-testnet.bybit.com/v5/public/linear"

# 로깅 관련 상수
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Update intervals (ms)
PRICE_UPDATE_INTERVAL_MS = 5000
STATUS_UPDATE_INTERVAL_MS = 1000

# Public price endpoint (fallback, no API key)
PUBLIC_PRICE_ENDPOINT = "https://api.binance.com/api/v3/ticker/price"

# Optional: route GUI updates via EventBus instead of direct signals
ENABLE_GUI_EVENTBUS = True

# Default PCS levels for ExitTab monitoring table
# Values reflect the UI demo but live logic should read from config when available.
PCS_DEFAULT_LEVELS = [
    {"step": 1,  "tp": 2.0,  "sl": -1.0},
    {"step": 2,  "tp": 4.0,  "sl": -2.0},
    {"step": 3,  "tp": 6.0,  "sl": -3.0},
    {"step": 4,  "tp": 8.0,  "sl": -4.0},
    {"step": 5,  "tp": 10.0, "sl": -5.0},
    {"step": 6,  "tp": 12.0, "sl": -6.0},
    {"step": 7,  "tp": 15.0, "sl": -8.0},
    {"step": 8,  "tp": 20.0, "sl": -10.0},
    {"step": 9,  "tp": 25.0, "sl": -12.0},
    {"step": 10, "tp": 30.0, "sl": -15.0},
    {"step": 11, "tp": 40.0, "sl": -20.0},
    {"step": 12, "tp": 50.0, "sl": -25.0},
]

# GUI 관련 상수
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600

TAB_NAMES = [
    "진입 설정",
    "청산 설정", 
    "시간 제어",
    "리스크 관리",
    "포지션 현황"
]

# 색상 상수
COLOR_GREEN = "#4CAF50"  # 매수/익절
COLOR_RED = "#F44336"    # 매도/손절
COLOR_BLUE = "#2196F3"   # 정보
COLOR_ORANGE = "#FF9800" # 경고
COLOR_GRAY = "#9E9E9E"   # 비활성화

# 상태 메시지
STATUS_DISCONNECTED = "연결 끊김"
STATUS_CONNECTING = "연결 중..."
STATUS_CONNECTED = "연결됨"
STATUS_TRADING = "거래 중"
STATUS_PAUSED = "일시정지"
STATUS_ERROR = "오류"

# 파일 경로
CONFIG_FILE = "config.json"
LOG_FILE = "trading_system.log"
DATA_DIR = "data"
BACKUP_DIR = "backup"

# 버전 정보
VERSION = "2.0.0"
BUILD_DATE = "2025-01-16"
AUTHOR = "Manus AI"


# GUI 색상 테마
GUI_COLORS = {
    "primary": "#007bff",
    "primary_light": "#66b3ff",
    "secondary": "#6c757d",
    "success": "#28a745",
    "success_light": "#5cbf6b",
    "success_hover": "#218838",
    "danger": "#dc3545",
    "danger_light": "#f5a6ae",
    "danger_hover": "#c82333",
    "warning": "#ffc107",
    "warning_light": "#ffda6a",
    "info": "#17a2b8",
    "light": "#f8f9fa",
    "dark": "#343a40",
    "accent": "#007bff",
    "accent_hover": "#0056b3",
    "background_primary": "#ffffff",
    "background_secondary": "#f8f9fa",
    "text_primary": "#212529",
    "text_secondary": "#6c757d",
    "text_disabled": "#adb5bd",
    "border": "#dee2e6"
}

# GUI 폰트
GUI_FONTS = {
    "default": "Arial",
    "monospace": "Courier New",
    "group_title": "Arial"
}

# GUI 크기
GUI_SIZES = {
    "spacing": 8,
    "margin": 10,
    "button_height": 32,
    "input_height": 28,
    "group_padding": 15
}

# 기본 설정
DEFAULT_SETTINGS = {
    "window_width": WINDOW_WIDTH,
    "window_height": WINDOW_HEIGHT,
    "update_interval": 1000,
    "auto_save": True,
    "theme": "light"
}
