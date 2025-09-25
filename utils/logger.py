"""
로깅 시스템 모듈

이 모듈은 시스템 전반의 로깅을 관리합니다.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional
from config.constants import LOG_LEVELS, DEFAULT_LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT, LOG_FILE


class ColoredFormatter(logging.Formatter):
    """컬러 로그 포매터"""
    
    # ANSI 색상 코드
    COLORS = {
        'DEBUG': '\033[36m',    # 청록색
        'INFO': '\033[32m',     # 녹색
        'WARNING': '\033[33m',  # 노란색
        'ERROR': '\033[31m',    # 빨간색
        'CRITICAL': '\033[35m', # 자주색
        'RESET': '\033[0m'      # 리셋
    }
    
    def format(self, record):
        """로그 레코드 포맷팅"""
        # 기본 포맷팅
        formatted = super().format(record)
        
        # 색상 적용
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        return f"{color}{formatted}{reset}"


def setup_logger(name: Optional[str] = None,
                level: str = "DEBUG",  # DEBUG로 변경하여 상세 로그 출력
                log_file: str = LOG_FILE,
                console_output: bool = True,
                file_output: bool = True) -> logging.Logger:
    """로거 설정"""
    
    # 로거 생성
    logger_name = name or "crypto_trading_system"
    logger = logging.getLogger(logger_name)
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 로그 레벨 설정
    if level.upper() in LOG_LEVELS:
        logger.setLevel(getattr(logging, level.upper()))
    else:
        logger.setLevel(logging.INFO)
    
    # 포매터 생성
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    colored_formatter = ColoredFormatter(LOG_FORMAT, LOG_DATE_FORMAT)
    
    # 콘솔 핸들러 추가
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(colored_formatter)
        logger.addHandler(console_handler)
    
    # 파일 핸들러 추가
    if file_output:
        try:
            # 로그 디렉토리 생성
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 회전 파일 핸들러 (최대 10MB, 5개 파일 유지)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            # 파일 핸들러 생성 실패 시 콘솔에만 출력
            logger.warning(f"파일 로그 핸들러 생성 실패: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """로거 반환"""
    return logging.getLogger(name)


class TradingLogger:
    """거래 전용 로거 클래스"""
    
    def __init__(self, name: str = "trading"):
        self.logger = get_logger(name)
        self.trade_file = f"trades_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 거래 전용 파일 핸들러
        try:
            trade_handler = logging.FileHandler(self.trade_file, encoding='utf-8')
            trade_formatter = logging.Formatter(
                "%(asctime)s - TRADE - %(message)s",
                LOG_DATE_FORMAT
            )
            trade_handler.setFormatter(trade_formatter)
            self.logger.addHandler(trade_handler)
        except Exception as e:
            self.logger.warning(f"거래 로그 파일 생성 실패: {e}")
    
    def log_entry(self, symbol: str, side: str, quantity: float, price: float, reason: str):
        """진입 로그"""
        message = f"ENTRY | {symbol} | {side} | {quantity} | {price} | {reason}"
        self.logger.info(message)
    
    def log_exit(self, symbol: str, side: str, quantity: float, price: float, pnl: float, reason: str):
        """청산 로그"""
        message = f"EXIT | {symbol} | {side} | {quantity} | {price} | PnL: {pnl} | {reason}"
        self.logger.info(message)
    
    def log_error(self, error_type: str, message: str, details: str = ""):
        """에러 로그"""
        error_message = f"ERROR | {error_type} | {message}"
        if details:
            error_message += f" | {details}"
        self.logger.error(error_message)
    
    def log_signal(self, signal_type: str, symbol: str, condition: str, confidence: float):
        """신호 로그"""
        message = f"SIGNAL | {signal_type} | {symbol} | {condition} | Confidence: {confidence:.2f}"
        self.logger.info(message)


class PerformanceLogger:
    """성능 측정 로거"""
    
    def __init__(self, name: str = "performance"):
        self.logger = get_logger(name)
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """타이머 시작"""
        self.start_times[operation] = datetime.now()
    
    def end_timer(self, operation: str):
        """타이머 종료 및 로그"""
        if operation in self.start_times:
            elapsed = datetime.now() - self.start_times[operation]
            elapsed_ms = elapsed.total_seconds() * 1000
            self.logger.debug(f"PERF | {operation} | {elapsed_ms:.2f}ms")
            del self.start_times[operation]
        else:
            self.logger.warning(f"타이머가 시작되지 않음: {operation}")
    
    def log_api_call(self, exchange: str, endpoint: str, duration_ms: float, success: bool):
        """API 호출 로그"""
        status = "SUCCESS" if success else "FAILED"
        message = f"API | {exchange} | {endpoint} | {duration_ms:.2f}ms | {status}"
        self.logger.info(message)
    
    def log_memory_usage(self, operation: str, memory_mb: float):
        """메모리 사용량 로그"""
        message = f"MEMORY | {operation} | {memory_mb:.2f}MB"
        self.logger.debug(message)


def log_function_call(func):
    """함수 호출 로깅 데코레이터"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"함수 호출: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"함수 완료: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"함수 오류: {func.__name__} - {e}")
            raise
    
    return wrapper


def log_async_function_call(func):
    """비동기 함수 호출 로깅 데코레이터"""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"비동기 함수 호출: {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"비동기 함수 완료: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"비동기 함수 오류: {func.__name__} - {e}")
            raise
    
    return wrapper


# 전역 로거 인스턴스
main_logger = None
trading_logger = None
performance_logger = None


def initialize_loggers(log_level: str = DEFAULT_LOG_LEVEL):
    """전역 로거 초기화"""
    global main_logger, trading_logger, performance_logger
    
    main_logger = setup_logger("main", log_level)
    trading_logger = TradingLogger()
    performance_logger = PerformanceLogger()
    
    main_logger.info("로깅 시스템 초기화 완료")


def get_main_logger() -> logging.Logger:
    """메인 로거 반환"""
    global main_logger
    if main_logger is None:
        main_logger = setup_logger("main")
    return main_logger


def get_trading_logger() -> TradingLogger:
    """거래 로거 반환"""
    global trading_logger
    if trading_logger is None:
        trading_logger = TradingLogger()
    return trading_logger


def get_performance_logger() -> PerformanceLogger:
    """성능 로거 반환"""
    global performance_logger
    if performance_logger is None:
        performance_logger = PerformanceLogger()
    return performance_logger
