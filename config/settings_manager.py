"""
설정 관리자 모듈

이 모듈은 시스템 전체의 설정을 관리합니다.
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from utils.logger import get_logger
from .constants import CONFIG_FILE, DEFAULT_SETTINGS

logger = get_logger(__name__)


@dataclass
class ExchangeConfig:
    """거래소 설정"""
    name: str
    api_key: str = ""
    api_secret: str = ""  # secret_key → api_secret으로 변경
    testnet: bool = True
    enabled: bool = True

    # 호환성을 위한 속성
    @property
    def secret_key(self):
        return self.api_secret

    @secret_key.setter
    def secret_key(self, value):
        self.api_secret = value


@dataclass
class TradingConfig:
    """거래 설정"""
    symbol: str = "BTCUSDT"
    leverage: int = 10
    position_size: float = 1000.0
    risk_percentage: float = 2.0
    max_positions: int = 5
    cooldown_minutes: int = 5
    min_confidence: float = 0.5


@dataclass
class EntryConfig:
    """진입 설정"""
    combination_mode: str = "AND"
    ma_enabled: bool = False
    ma_period: int = 4
    ma_condition: str = "close_above"
    pc_enabled: bool = False
    pc_period: int = 20
    pc_condition: str = "upper_buy"
    orderbook_enabled: bool = False
    candle_enabled: bool = False
    tick_enabled: bool = False

    # MA Cross 설정 추가
    ma_cross: Optional[Dict[str, Any]] = None
    price_channel: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # ma_cross 기본값 설정
        if self.ma_cross is None:
            self.ma_cross = {
                "enabled": False,
                "short_period": 50,
                "long_period": 200,
                "confidence_threshold": 0.6
            }
        # price_channel 기본값 설정
        if self.price_channel is None:
            self.price_channel = {
                "enabled": False,
                "period": 20,
                "breakout_threshold": 0.5
            }


@dataclass
class ExitConfig:
    """청산 설정"""
    pcs_enabled: bool = True
    pcs_steps: list = None
    trailing_enabled: bool = False
    trailing_percentage: float = 2.0
    tick_exit_enabled: bool = False
    breakeven_enabled: bool = False

    # PCS 시스템 설정 추가
    pcs_system: Optional[Dict[str, Any]] = None
    pct: Optional[Dict[str, Any]] = None
    orderbook_exit: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.pcs_steps is None:
            # 기본 PCS 12단계 설정
            self.pcs_steps = [
                {"step": i+1, "percentage": (i+1)*2, "enabled": True}
                for i in range(12)
            ]

        # pcs_system 기본값 설정
        if self.pcs_system is None:
            self.pcs_system = {
                "enabled": True,
                "steps": self.pcs_steps if self.pcs_steps else []
            }

        # pct 기본값 설정
        if self.pct is None:
            self.pct = {
                "enabled": False,
                "channel_period": 20,
                "trailing_offset": 2.0,
                "activation_profit": 2.0
            }

        # orderbook_exit 기본값 설정
        if self.orderbook_exit is None:
            self.orderbook_exit = {
                "enabled": False,
                "imbalance_ratio": 2.0,
                "depth_levels": 5,
                "consecutive_signals": 3
            }


@dataclass
class TimeConfig:
    """시간 제어 설정"""
    enabled: bool = False
    weekday_settings: dict = None
    always_on: bool = True
    exclude_holidays: bool = False
    
    def __post_init__(self):
        if self.weekday_settings is None:
            self.weekday_settings = {
                "monday": {"enabled": True, "start": "00:00", "end": "23:59"},
                "tuesday": {"enabled": True, "start": "00:00", "end": "23:59"},
                "wednesday": {"enabled": True, "start": "00:00", "end": "23:59"},
                "thursday": {"enabled": True, "start": "00:00", "end": "23:59"},
                "friday": {"enabled": True, "start": "00:00", "end": "23:59"},
                "saturday": {"enabled": True, "start": "00:00", "end": "23:59"},
                "sunday": {"enabled": True, "start": "00:00", "end": "23:59"}
            }


@dataclass
class RiskConfig:
    """리스크 관리 설정"""
    max_leverage: int = 10
    position_mode: str = "단방향"
    auto_leverage: bool = False
    max_daily_loss: float = 5.0
    max_position_size: float = 10000.0
    stop_loss_percentage: float = 2.0
    take_profit_percentage: float = 4.0


@dataclass
class AppConfig:
    """전체 애플리케이션 설정"""
    exchanges: list = None
    trading: TradingConfig = None
    entry: EntryConfig = None
    exit: ExitConfig = None
    time: TimeConfig = None
    risk: RiskConfig = None
    gui: dict = None
    
    def __post_init__(self):
        if self.exchanges is None:
            self.exchanges = [
                ExchangeConfig("binance"),
                ExchangeConfig("bybit")
            ]
        if self.trading is None:
            self.trading = TradingConfig()
        if self.entry is None:
            self.entry = EntryConfig()
        if self.exit is None:
            self.exit = ExitConfig()
        if self.time is None:
            self.time = TimeConfig()
        if self.risk is None:
            self.risk = RiskConfig()
        if self.gui is None:
            self.gui = DEFAULT_SETTINGS.copy()


class SettingsManager:
    """설정 관리자 클래스 (싱글톤)"""

    _instance = None
    _initialized = False

    def __new__(cls, config_file: str = CONFIG_FILE):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_file: str = CONFIG_FILE):
        # 이미 초기화되었으면 스킵
        if SettingsManager._initialized:
            return

        self.config_file = config_file
        self.config = AppConfig()
        self.load_config()
        SettingsManager._initialized = True
    
    def load_config(self) -> None:
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 데이터를 AppConfig 객체로 변환
                self.config = self._dict_to_config(data)
                logger.info(f"설정 파일 로드 완료: {self.config_file}")
            else:
                logger.info(f"설정 파일이 없습니다: {self.config_file}. 기본 설정을 사용합니다.")
                self.save_config()  # 기본 설정으로 파일 생성
                
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            self.config = AppConfig()  # 기본 설정 사용
    
    def save_config(self) -> None:
        """설정 파일 저장"""
        try:
            # AppConfig 객체를 딕셔너리로 변환
            data = self._config_to_dict(self.config)
            
            # 메타데이터 추가
            data['_metadata'] = {
                'version': '2.0.0',
                'created': datetime.now().isoformat(),
                'description': '암호화폐 자동매매 시스템 설정'
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"설정 파일 저장 완료: {self.config_file}")
            
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
    
    def _config_to_dict(self, config: AppConfig) -> Dict[str, Any]:
        """AppConfig 객체를 딕셔너리로 변환"""
        return {
            'exchanges': [asdict(exchange) for exchange in config.exchanges],
            'trading': asdict(config.trading),
            'entry': asdict(config.entry),
            'exit': asdict(config.exit),
            'time': asdict(config.time),
            'risk': asdict(config.risk),
            'gui': config.gui
        }
    
    def _dict_to_config(self, data: Dict[str, Any]) -> AppConfig:
        """딕셔너리를 AppConfig 객체로 변환"""
        config = AppConfig()
        
        # 거래소 설정
        if 'exchanges' in data:
            config.exchanges = [
                ExchangeConfig(**exchange_data) 
                for exchange_data in data['exchanges']
            ]
        
        # 거래 설정
        if 'trading' in data:
            config.trading = TradingConfig(**data['trading'])
        
        # 진입 설정
        if 'entry' in data:
            config.entry = EntryConfig(**data['entry'])
        
        # 청산 설정
        if 'exit' in data:
            config.exit = ExitConfig(**data['exit'])
        
        # 시간 설정
        if 'time' in data:
            config.time = TimeConfig(**data['time'])
        
        # 리스크 설정
        if 'risk' in data:
            config.risk = RiskConfig(**data['risk'])
        
        # GUI 설정
        if 'gui' in data:
            config.gui = data['gui']
        
        return config
    
    def get_exchange_config(self, exchange_name: str) -> Optional[ExchangeConfig]:
        """특정 거래소 설정 반환"""
        for exchange in self.config.exchanges:
            if exchange.name == exchange_name:
                return exchange
        return None
    
    def update_exchange_config(self, exchange_name: str, **kwargs) -> None:
        """거래소 설정 업데이트"""
        for exchange in self.config.exchanges:
            if exchange.name == exchange_name:
                for key, value in kwargs.items():
                    if hasattr(exchange, key):
                        setattr(exchange, key, value)
                break
        self.save_config()
    
    def update_trading_config(self, **kwargs) -> None:
        """거래 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self.config.trading, key):
                setattr(self.config.trading, key, value)
        self.save_config()
    
    def update_entry_config(self, **kwargs) -> None:
        """진입 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self.config.entry, key):
                setattr(self.config.entry, key, value)
        self.save_config()
    
    def update_exit_config(self, **kwargs) -> None:
        """청산 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self.config.exit, key):
                setattr(self.config.exit, key, value)
        self.save_config()
    
    def update_time_config(self, **kwargs) -> None:
        """시간 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self.config.time, key):
                setattr(self.config.time, key, value)
        self.save_config()
    
    def update_risk_config(self, **kwargs) -> None:
        """리스크 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self.config.risk, key):
                setattr(self.config.risk, key, value)
        self.save_config()
    
    def update_gui_config(self, **kwargs) -> None:
        """GUI 설정 업데이트"""
        self.config.gui.update(kwargs)
        self.save_config()
    
    def reset_to_defaults(self) -> None:
        """기본 설정으로 리셋"""
        self.config = AppConfig()
        self.save_config()
        logger.info("설정이 기본값으로 리셋되었습니다")
    
    def export_config(self, file_path: str) -> None:
        """설정을 다른 파일로 내보내기"""
        try:
            data = self._config_to_dict(self.config)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"설정 내보내기 완료: {file_path}")
        except Exception as e:
            logger.error(f"설정 내보내기 실패: {e}")
    
    def import_config(self, file_path: str) -> None:
        """다른 파일에서 설정 가져오기"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.config = self._dict_to_config(data)
            self.save_config()
            logger.info(f"설정 가져오기 완료: {file_path}")
        except Exception as e:
            logger.error(f"설정 가져오기 실패: {e}")


# 전역 설정 관리자 인스턴스
_settings_manager = None


def get_settings_manager() -> SettingsManager:
    """전역 설정 관리자 반환"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def get_config() -> AppConfig:
    """현재 설정 반환"""
    return get_settings_manager().config
