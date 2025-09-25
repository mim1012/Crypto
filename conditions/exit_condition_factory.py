"""
청산 조건 팩토리 모듈

이 모듈은 다양한 청산 조건을 생성하는 팩토리를 제공합니다.
"""

from typing import Dict, Any, List, Optional
from conditions.base_condition import BaseCondition, ExitCondition
from core.models import Position, MarketData
from config.settings_manager import get_settings_manager
from config.constants import PCS_DEFAULT_LEVELS
from utils.logger import get_logger

logger = get_logger(__name__)


class PCSSystemCondition(ExitCondition):
    """PCS 12단계 출구 로직 (TP/SL 기반)
    - 활성 스텝의 TP/SL 임계치를 PnL%와 비교해 EXIT 신호를 생성
    - 임계치 소스: config.exit.pcs_steps > PCS_DEFAULT_LEVELS
    """

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.active_steps = params.get("active_steps", [1, 2, 3, 4, 5, 6])
        self.auto_leverage = params.get("auto_leverage", True)
        name = f"PCS System (steps: {self.active_steps})"
        super().__init__(name, config)
        # PCS 임계치: 설정(config.exit.pcs_steps) 우선, 없으면 상수로 폴백
        self.pcs_levels = self._load_pcs_levels_from_config()

    def get_active_levels(self):
        """활성화된 PCS 레벨 목록"""
        return [lv for lv in self.pcs_levels if lv.get("enabled", True) and lv["step"] in set(self.active_steps)]

    def evaluate(self, market_data: MarketData, position: Optional[Position] = None):
        """활성 스텝 기준 TP/SL 충족 시 EXIT 신호 생성."""
        if not position or not self._validate_position(position):
            return None
        try:
            pnl_pct = float(position.calculate_pnl_percentage())
        except Exception:
            return None

        active_levels = self.get_active_levels()
        if not active_levels:
            return None

        tp_candidates = [lv for lv in active_levels if pnl_pct >= lv["tp"]]
        sl_candidates = [lv for lv in active_levels if pnl_pct <= lv["sl"]]

        chosen = None
        reason = None
        confidence = 0.8
        if sl_candidates:
            chosen = sorted(sl_candidates, key=lambda x: x["step"])[0]
            reason = "SL"
            confidence = 0.9
        elif tp_candidates:
            chosen = sorted(tp_candidates, key=lambda x: x["step"], reverse=True)[0]
            reason = "TP"
            confidence = 0.8

        if not chosen:
            return None

        metadata = {
            "pcs_step": chosen["step"],
            "pcs_tp": chosen["tp"],
            "pcs_sl": chosen["sl"],
            "reason": reason,
            "pnl_pct": pnl_pct,
        }
        return self._create_exit_signal(market_data, position, confidence, metadata)

    def _load_pcs_levels_from_config(self):
        """config.exit.pcs_steps를 1차 소스로 사용하고, 없으면 상수로 대체한다."""
        try:
            cfg = get_settings_manager().config
            steps = cfg.exit.pcs_steps or []
            levels = []
            for step_entry in steps:
                step_no = int(step_entry.get('step'))
                enabled = bool(step_entry.get('enabled', True))
                const = next((lv for lv in PCS_DEFAULT_LEVELS if lv['step'] == step_no), None)
                tp = float(step_entry.get('tp', const['tp'] if const else 0.0))
                sl = float(step_entry.get('sl', const['sl'] if const else 0.0))
                levels.append({"step": step_no, "tp": tp, "sl": sl, "enabled": enabled})
            if levels:
                return levels
        except Exception:
            pass
        return [{"step": lv["step"], "tp": lv["tp"], "sl": lv["sl"], "enabled": True} for lv in PCS_DEFAULT_LEVELS]


class PCTrailingCondition(BaseCondition):
    """PC 트레일링 청산"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.period = params.get("period", "4시간봉")
        self.condition = params.get("condition", "하단 터치")
        self.distance = params.get("distance", "PC 중심선")
        name = f"PC Trailing ({self.period})"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """트레일링 스탑 조건 평가"""
        # 실제 구현은 market_data에서 Price Channel을 계산하고
        # 설정된 조건에 따라 트레일링 스탑 신호 생성
        return None


class TickExitCondition(BaseCondition):
    """호가 청산 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.loss_ticks = params.get("loss_ticks", 10)
        self.profit_ticks = params.get("profit_ticks", 20)
        self.condition = params.get("condition", "즉시 청산")
        name = f"Tick Exit (손실{self.loss_ticks}/수익{self.profit_ticks}틱)"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """호가 기반 청산 조건 평가"""
        # 실제 구현은 market_data의 호가 정보를 분석하여
        # 틱 기준 청산 신호 생성
        return None


class PCBreakevenCondition(BaseCondition):
    """PC 본절 청산 조건 - PC선 터치 후 틱 이동 청산"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.condition = params.get("condition", "수익 2% 이상 시 본절")
        self.margin = params.get("margin", "0.1% 여유")
        self.timing = params.get("timing", "즉시 적용")

        # 틱 설정 추가
        self.long_ticks = params.get("long_ticks", 10)  # 매수: 하단선 터치 후 하락 틱
        self.short_ticks = params.get("short_ticks", 10)  # 매도: 상단선 터치 후 상승 틱

        # PC선 터치 상태 추적
        self.pc_touched = False
        self.touch_price = None
        self.tick_size = 0.01  # 기본 틱 사이즈 (심볼별로 조정 필요)

        # 본절 조건에서 퍼센트 추출
        self.breakeven_threshold = self._parse_threshold(self.condition)
        name = f"PC Breakeven (Long: {self.long_ticks}틱, Short: {self.short_ticks}틱)"
        super().__init__(name, config)

    def _parse_threshold(self, condition: str) -> float:
        """본절 조건에서 임계값 추출"""
        try:
            # "수익 X% 이상 시 본절" 형식에서 X 추출
            import re
            match = re.search(r'수익\s+(\d+(?:\.\d+)?)', condition)
            if match:
                return float(match.group(1))
            return 2.0  # 기본값
        except:
            return 2.0

    def evaluate(self, market_data, position=None):
        """PC선 터치 후 틱 이동 청산 조건 평가"""
        if not position or not market_data:
            return None

        current_price = market_data.current_price

        # PC 채널 계산 (20일 기준)
        if len(market_data.high_prices) < 20:
            return None

        pc_upper = max(market_data.high_prices[-20:])
        pc_lower = min(market_data.low_prices[-20:])

        # 매수 포지션
        from core.models import PositionSide
        if position.side == PositionSide.LONG or position.side == "BUY":
            # 1단계: PC 하단선 터치 체크
            if not self.pc_touched and current_price <= pc_lower:
                self.pc_touched = True
                self.touch_price = pc_lower
                print(f"[PC 본절] 매수 포지션 - 하단선 터치! 가격: {pc_lower}")

            # 2단계: 터치 후 추가 하락 체크
            if self.pc_touched and self.touch_price:
                tick_move = (self.touch_price - current_price) / self.tick_size
                if tick_move >= self.long_ticks:
                    print(f"[PC 본절] 매수 포지션 청산! {tick_move:.1f}틱 하락")
                    self.pc_touched = False
                    self.touch_price = None
                    return {"action": "close", "reason": f"PC 하단선 터치 후 {self.long_ticks}틱 하락"}

        # 매도 포지션
        elif position.side == PositionSide.SHORT or position.side == "SELL":
            # 1단계: PC 상단선 터치 체크
            if not self.pc_touched and current_price >= pc_upper:
                self.pc_touched = True
                self.touch_price = pc_upper
                print(f"[PC 본절] 매도 포지션 - 상단선 터치! 가격: {pc_upper}")

            # 2단계: 터치 후 추가 상승 체크
            if self.pc_touched and self.touch_price:
                tick_move = (current_price - self.touch_price) / self.tick_size
                if tick_move >= self.short_ticks:
                    print(f"[PC 본절] 매도 포지션 청산! {tick_move:.1f}틱 상승")
                    self.pc_touched = False
                    self.touch_price = None
                    return {"action": "close", "reason": f"PC 상단선 터치 후 {self.short_ticks}틱 상승"}

        return None


class TickAdditionalEntryCondition(BaseCondition):
    """틱 기반 추가 진입 조건"""

    def __init__(self, config: Dict[str, Any]):
        params = config.get("params", {})
        self.up_ticks = params.get("up_ticks", 8)      # 상승 틱
        self.down_ticks = params.get("down_ticks", 8)  # 하락 틱
        self.ratio = params.get("ratio", 30.0)         # 추가 진입 비율
        self.tick_size = 0.01  # 기본 틱 사이즈

        # 추가 진입 상태 추적
        self.last_entry_price = None
        self.additional_entries = 0
        self.max_additional_entries = 3  # 최대 추가 진입 횟수

        name = f"Tick Additional Entry (Up: {self.up_ticks}틱, Down: {self.down_ticks}틱, Ratio: {self.ratio}%)"
        super().__init__(name, config)

    def evaluate(self, market_data, position=None):
        """틱 기반 추가 진입 조건 평가"""
        if not market_data:
            return None

        current_price = market_data.current_price

        # 포지션이 있고 추가 진입 가능한 경우
        if position and self.additional_entries < self.max_additional_entries:
            from core.models import PositionSide

            # 매수 포지션인 경우
            if position.side == PositionSide.LONG or position.side == "BUY":
                # 평균 진입가 대비 하락 틱 체크
                tick_move = (position.entry_price - current_price) / self.tick_size

                if tick_move >= self.down_ticks:
                    self.additional_entries += 1
                    additional_size = position.size * (self.ratio / 100)

                    return {
                        "action": "add_position",
                        "size": additional_size,
                        "reason": f"{self.down_ticks}틱 하락으로 {self.ratio}% 추가 진입"
                    }

            # 매도 포지션인 경우
            elif position.side == PositionSide.SHORT or position.side == "SELL":
                # 평균 진입가 대비 상승 틱 체크
                tick_move = (current_price - position.entry_price) / self.tick_size

                if tick_move >= self.up_ticks:
                    self.additional_entries += 1
                    additional_size = position.size * (self.ratio / 100)

                    return {
                        "action": "add_position",
                        "size": additional_size,
                        "reason": f"{self.up_ticks}틱 상승으로 {self.ratio}% 추가 진입"
                    }

        return None


class ExitConditionFactory:
    """청산 조건 팩토리"""

    # 청산 조건 타입 매핑
    CONDITION_CLASSES = {
        "pcs_system": PCSSystemCondition,
        "pc_trailing": PCTrailingCondition,
        "tick_exit": TickExitCondition,
        "pc_breakeven": PCBreakevenCondition,
        "tick_additional": TickAdditionalEntryCondition,  # 틱 기반 추가 진입
    }

    @classmethod
    def create_condition(cls, config: Dict[str, Any]) -> BaseCondition:
        """청산 조건 생성

        Args:
            config: 청산 조건 설정
                - type: 조건 타입 (pcs_system, pc_trailing, tick_exit, pc_breakeven)
                - enabled: 활성화 여부
                - params: 조건별 파라미터

        Returns:
            생성된 청산 조건 인스턴스
        """
        condition_type = config.get("type")

        if not condition_type:
            raise ValueError("청산 조건 타입이 지정되지 않았습니다")

        condition_class = cls.CONDITION_CLASSES.get(condition_type)

        if not condition_class:
            raise ValueError(f"지원하지 않는 청산 조건 타입: {condition_type}")

        try:
            condition = condition_class(config)
            logger.info(f"청산 조건 생성 완료: {condition.get_name()}")
            return condition

        except Exception as e:
            logger.error(f"청산 조건 생성 실패: {condition_type} - {e}")
            raise



