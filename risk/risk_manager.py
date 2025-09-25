"""
리스크 관리 모듈

이 모듈은 거래 리스크를 관리하고 제한합니다.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RiskLimits:
    """리스크 제한 설정"""
    max_leverage: int = 10
    max_positions: int = 3
    max_position_size_percent: float = 10.0  # 잔고 대비 %
    daily_max_trades: int = 50
    daily_loss_limit_percent: float = 5.0  # 일일 최대 손실 %
    auto_adjust_leverage: bool = True
    position_mode: str = "단방향"  # 단방향/양방향


class RiskManager:
    """리스크 관리자"""

    def __init__(self, config: Dict[str, Any]):
        """리스크 관리자 초기화

        Args:
            config: 리스크 관리 설정
        """
        self.config = config
        self.logger = logger  # logger 속성 추가

        # 레버리지 설정
        leverage_config = config.get("leverage", {})
        self.max_leverage = leverage_config.get("max_leverage", 10)
        self.position_mode = leverage_config.get("position_mode", "단방향")
        self.auto_adjust_leverage = leverage_config.get("auto_adjust", True)

        # 포지션 제한 설정
        position_config = config.get("position_limits", {})
        self.max_positions = position_config.get("max_positions", 3)
        self.max_position_size = self._parse_position_size(
            position_config.get("max_position_size", "10%")
        )
        self.daily_max_trades = position_config.get("daily_max_trades", 50)
        self.daily_limit = self._parse_daily_limit(
            position_config.get("daily_limit", "5%")
        )

        # 손절 설정
        stop_config = config.get("stop_loss", {})
        self.auto_stop = stop_config.get("auto_stop", True)
        self.stop_levels = stop_config.get("levels", [])

        # 거래 추적
        self.daily_trades = 0
        self.daily_loss = 0.0
        self.last_reset_date = datetime.now().date()
        self.active_positions = []

        logger.info(f"리스크 관리자 초기화: 최대 레버리지 {self.max_leverage}배, 최대 포지션 {self.max_positions}개")

    def _parse_position_size(self, size_str: str) -> float:
        """포지션 크기 문자열 파싱"""
        try:
            if "%" in size_str:
                return float(size_str.replace("%", "").strip())
            elif "USDT" in size_str:
                return float(size_str.replace("USDT", "").replace(",", "").strip())
            return 10.0
        except:
            return 10.0

    def _parse_daily_limit(self, limit_str: str) -> float:
        """일일 제한 문자열 파싱"""
        try:
            if "%" in limit_str:
                return float(limit_str.replace("%", "").strip())
            elif "USDT" in limit_str:
                return float(limit_str.replace("USDT", "").replace(",", "").strip())
            return 5.0
        except:
            return 5.0

    def validate_entry_signal(self, signal) -> bool:
        """진입 신호 검증

        Args:
            signal: 진입 신호

        Returns:
            진입 가능 여부
        """
        # 일일 거래 횟수 체크
        if not self._check_daily_trades():
            logger.warning("일일 거래 횟수 초과")
            return False

        # 최대 포지션 수 체크
        if not self._check_max_positions():
            logger.warning("최대 포지션 수 초과")
            return False

        # 일일 손실 제한 체크
        if not self._check_daily_loss():
            logger.warning("일일 손실 제한 초과")
            return False

        # 포지션 크기 체크
        if not self._check_position_size(signal):
            logger.warning("포지션 크기 초과")
            return False

        return True

    def _check_daily_trades(self) -> bool:
        """일일 거래 횟수 확인"""
        # 날짜가 변경되면 카운터 리셋
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_trades = 0
            self.daily_loss = 0.0
            self.last_reset_date = current_date

        return self.daily_trades < self.daily_max_trades

    def _check_max_positions(self) -> bool:
        """최대 포지션 수 확인"""
        return len(self.active_positions) < self.max_positions

    def _check_daily_loss(self) -> bool:
        """일일 손실 제한 확인"""
        # 계좌 잔고 대비 일일 손실 계산
        if self.account_balance > 0:
            daily_loss_pct = (self.daily_pnl / self.account_balance) * 100
            if daily_loss_pct <= -self.daily_loss_limit:
                self.logger.warning(f"일일 손실 한도 초과: {daily_loss_pct:.2f}% (한도: -{self.daily_loss_limit}%)")
                return False
        return True

    def _check_position_size(self, signal) -> bool:
        """포지션 크기 확인"""
        # 계좌 잔고 대비 포지션 크기 계산
        if self.account_balance > 0:
            position_value = getattr(signal, 'position_value', self.max_position_size)
            position_pct = (position_value / self.account_balance) * 100
            if position_pct > self.max_position_size:
                self.logger.warning(f"포지션 크기 초과: {position_pct:.2f}% (최대: {self.max_position_size}%)")
                return False
        return True

    def calculate_position_size(self, account_balance: float, current_price: float) -> float:
        """포지션 크기 계산

        Args:
            account_balance: 계좌 잔고
            current_price: 현재 가격

        Returns:
            포지션 크기 (계약 수)
        """
        # 잔고의 일정 비율로 포지션 크기 결정
        position_value = account_balance * (self.max_position_size / 100)

        # 레버리지 적용
        leveraged_value = position_value * self.max_leverage

        # 계약 수 계산
        contracts = leveraged_value / current_price

        return contracts

    def get_stop_loss_price(self, entry_price: float, side: str, level: int = 1) -> Optional[float]:
        """손절 가격 계산

        Args:
            entry_price: 진입 가격
            side: 포지션 방향 (LONG/SHORT)
            level: 손절 레벨 (1-12)

        Returns:
            손절 가격
        """
        if not self.auto_stop or level > len(self.stop_levels):
            return None

        # 해당 레벨의 손절 비율 가져오기
        _, _, stop_percent = self.stop_levels[level - 1]

        if side == "LONG":
            stop_price = entry_price * (1 - stop_percent / 100)
        else:  # SHORT
            stop_price = entry_price * (1 + stop_percent / 100)

        return stop_price

    def get_take_profit_price(self, entry_price: float, side: str, level: int = 1) -> Optional[float]:
        """익절 가격 계산

        Args:
            entry_price: 진입 가격
            side: 포지션 방향 (LONG/SHORT)
            level: 익절 레벨 (1-12)

        Returns:
            익절 가격
        """
        if not self.auto_stop or level > len(self.stop_levels):
            return None

        # 해당 레벨의 익절 비율 가져오기
        _, profit_percent, _ = self.stop_levels[level - 1]

        if side == "LONG":
            profit_price = entry_price * (1 + profit_percent / 100)
        else:  # SHORT
            profit_price = entry_price * (1 - profit_percent / 100)

        return profit_price

    def update_position_opened(self, position):
        """포지션 진입 시 업데이트"""
        self.active_positions.append(position)
        self.daily_trades += 1
        logger.info(f"포지션 진입: 일일 거래 {self.daily_trades}/{self.daily_max_trades}")

    def update_position_closed(self, position, pnl: float):
        """포지션 청산 시 업데이트"""
        if position in self.active_positions:
            self.active_positions.remove(position)

        if pnl < 0:
            self.daily_loss += abs(pnl)

        logger.info(f"포지션 청산: PnL {pnl:.2f}, 일일 손실 {self.daily_loss:.2f}")

    def get_adjusted_leverage(self, volatility: float) -> int:
        """변동성에 따른 레버리지 조정

        Args:
            volatility: 현재 변동성

        Returns:
            조정된 레버리지
        """
        if not self.auto_adjust_leverage:
            return self.max_leverage

        # 변동성이 높을수록 레버리지 감소
        if volatility > 5.0:
            return max(1, self.max_leverage // 3)
        elif volatility > 3.0:
            return max(1, self.max_leverage // 2)
        elif volatility > 2.0:
            return max(1, int(self.max_leverage * 0.7))
        else:
            return self.max_leverage

    def reset_daily_counters(self):
        """일일 카운터 리셋 (수동)"""
        self.daily_trades = 0
        self.daily_loss = 0.0
        self.last_reset_date = datetime.now().date()
        logger.info("일일 카운터 리셋 완료")

    def get_risk_status(self) -> Dict[str, Any]:
        """현재 리스크 상태 반환"""
        return {
            "max_leverage": self.max_leverage,
            "active_positions": len(self.active_positions),
            "max_positions": self.max_positions,
            "daily_trades": self.daily_trades,
            "daily_max_trades": self.daily_max_trades,
            "daily_loss": self.daily_loss,
            "daily_limit": self.daily_limit,
            "auto_stop": self.auto_stop
        }