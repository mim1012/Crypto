"""
설정 관리 모듈

이 모듈은 애플리케이션의 모든 설정을 관리합니다.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExchangeConfig:
    """거래소 설정"""
    name: str
    api_key: str
    secret_key: str
    testnet: bool = False
    enabled: bool = True
    
    def __post_init__(self):
        """초기화 후 검증"""
        if not self.name:
            raise ValueError("거래소 이름은 필수입니다")
        if not self.api_key:
            raise ValueError("API 키는 필수입니다")
        if not self.secret_key:
            raise ValueError("Secret 키는 필수입니다")


@dataclass
class TradingConfig:
    """거래 설정"""
    leverage: int = 10
    max_positions: int = 5
    position_size: float = 1000.0
    risk_percentage: float = 2.0
    max_daily_trades: int = 50
    daily_loss_limit: float = 5.0
    
    def __post_init__(self):
        """초기화 후 검증"""
        if self.leverage < 1 or self.leverage > 125:
            raise ValueError("레버리지는 1-125 사이여야 합니다")
        if self.max_positions < 1 or self.max_positions > 10:
            raise ValueError("최대 포지션 수는 1-10 사이여야 합니다")
        if self.risk_percentage < 0.1 or self.risk_percentage > 10:
            raise ValueError("리스크 비율은 0.1-10% 사이여야 합니다")


@dataclass
class EntryConditionConfig:
    """진입 조건 설정"""
    moving_average: Dict[str, Any]
    price_channel: Dict[str, Any]
    orderbook: Dict[str, Any]
    tick_based: Dict[str, Any]
    candle_state: Dict[str, Any]
    combination_mode: str = "OR"  # "AND" or "OR"
    
    @classmethod
    def default(cls) -> 'EntryConditionConfig':
        """기본 설정 반환"""
        return cls(
            moving_average={
                "enabled": False,
                "period": 20,
                "condition_type": "close_above",
                "signal_type": "BUY"
            },
            price_channel={
                "enabled": False,
                "period": 20,
                "upper_breakout": "none",
                "lower_breakout": "none"
            },
            orderbook={
                "enabled": False,
                "tick_threshold": 5,
                "direction": "both"
            },
            tick_based={
                "enabled": False,
                "up_ticks": 3,
                "down_ticks": 3,
                "additional_ratio": 50
            },
            candle_state={
                "enabled": False,
                "bullish_action": "none",
                "bearish_action": "none"
            }
        )


@dataclass
class ExitConditionConfig:
    """청산 조건 설정"""
    pcs_enabled: bool = False
    pcs_steps: List[bool] = None
    pc_trailing_enabled: bool = False
    orderbook_exit_enabled: bool = False
    pc_breakout_enabled: bool = False
    auto_leverage_adjustment: bool = False
    
    def __post_init__(self):
        """초기화 후 PCS 단계 설정"""
        if self.pcs_steps is None:
            self.pcs_steps = [False] * 12  # 12단계 모두 비활성화


@dataclass
class TimeControlConfig:
    """시간 제어 설정"""
    enabled: bool = False
    weekdays: Dict[str, Dict[str, Any]] = None
    force_close_time: Optional[str] = None
    run_24h: bool = False
    exclude_holidays: bool = True
    
    def __post_init__(self):
        """초기화 후 요일 설정"""
        if self.weekdays is None:
            self.weekdays = {
                day: {
                    "active": False,
                    "secondary": False,
                    "force_close": False,
                    "start_time": "09:00",
                    "end_time": "15:30"
                }
                for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            }


@dataclass
class AppConfig:
    """애플리케이션 전체 설정"""
    exchanges: List[ExchangeConfig]
    trading: TradingConfig
    entry_conditions: EntryConditionConfig
    exit_conditions: ExitConditionConfig
    time_control: TimeControlConfig
    log_level: str = "INFO"
    gui_theme: str = "default"
    auto_save: bool = True
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'AppConfig':
        """설정 파일에서 로드"""
        try:
            if not os.path.exists(config_path):
                logger.warning(f"설정 파일이 없습니다: {config_path}. 기본 설정을 사용합니다.")
                return cls.default()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 거래소 설정 파싱
            exchanges = [ExchangeConfig(**exchange) for exchange in data.get('exchanges', [])]
            
            # 거래 설정 파싱
            trading = TradingConfig(**data.get('trading', {}))
            
            # 진입 조건 설정 파싱
            entry_data = data.get('entry_conditions', {})
            entry_conditions = EntryConditionConfig(**entry_data) if entry_data else EntryConditionConfig.default()
            
            # 청산 조건 설정 파싱
            exit_data = data.get('exit_conditions', {})
            exit_conditions = ExitConditionConfig(**exit_data) if exit_data else ExitConditionConfig()
            
            # 시간 제어 설정 파싱
            time_data = data.get('time_control', {})
            time_control = TimeControlConfig(**time_data) if time_data else TimeControlConfig()
            
            config = cls(
                exchanges=exchanges,
                trading=trading,
                entry_conditions=entry_conditions,
                exit_conditions=exit_conditions,
                time_control=time_control,
                log_level=data.get('log_level', 'INFO'),
                gui_theme=data.get('gui_theme', 'default'),
                auto_save=data.get('auto_save', True)
            )
            
            logger.info(f"설정 파일 로드 완료: {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            logger.info("기본 설정을 사용합니다.")
            return cls.default()
    
    def save_to_file(self, config_path: str) -> None:
        """설정 파일에 저장"""
        try:
            # 데이터클래스를 딕셔너리로 변환
            data = asdict(self)
            
            # JSON 파일로 저장
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"설정 파일 저장 완료: {config_path}")
            
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
            raise
    
    @classmethod
    def default(cls) -> 'AppConfig':
        """기본 설정 반환"""
        return cls(
            exchanges=[
                ExchangeConfig(
                    name="binance",
                    api_key="your_binance_api_key",
                    secret_key="your_binance_secret_key",
                    testnet=True,
                    enabled=True
                ),
                ExchangeConfig(
                    name="bybit",
                    api_key="your_bybit_api_key",
                    secret_key="your_bybit_secret_key",
                    testnet=True,
                    enabled=True
                )
            ],
            trading=TradingConfig(),
            entry_conditions=EntryConditionConfig.default(),
            exit_conditions=ExitConditionConfig(),
            time_control=TimeControlConfig()
        )
    
    def validate(self) -> bool:
        """설정 유효성 검증"""
        try:
            # 거래소 설정 검증
            if not self.exchanges:
                raise ValueError("최소 하나의 거래소 설정이 필요합니다")
            
            enabled_exchanges = [ex for ex in self.exchanges if ex.enabled]
            if not enabled_exchanges:
                raise ValueError("최소 하나의 거래소가 활성화되어야 합니다")
            
            # 거래 설정 검증
            if self.trading.position_size <= 0:
                raise ValueError("포지션 크기는 0보다 커야 합니다")
            
            logger.info("설정 검증 완료")
            return True
            
        except Exception as e:
            logger.error(f"설정 검증 실패: {e}")
            return False
    
    def get_exchange_config(self, exchange_name: str) -> Optional[ExchangeConfig]:
        """특정 거래소 설정 반환"""
        for exchange in self.exchanges:
            if exchange.name == exchange_name and exchange.enabled:
                return exchange
        return None
    
    def update_exchange_config(self, exchange_name: str, **kwargs) -> None:
        """거래소 설정 업데이트"""
        for exchange in self.exchanges:
            if exchange.name == exchange_name:
                for key, value in kwargs.items():
                    if hasattr(exchange, key):
                        setattr(exchange, key, value)
                break
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    def __str__(self) -> str:
        """문자열 표현"""
        enabled_exchanges = [ex.name for ex in self.exchanges if ex.enabled]
        return f"AppConfig(exchanges={enabled_exchanges}, leverage={self.trading.leverage})"
