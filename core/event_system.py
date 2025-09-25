"""
안정 버전의 이벤트 시스템

필요한 인터페이스(EventType, Event, EventHandler, publish/subscribe,
start_event_system/stop_event_system)만 최소 구현합니다.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from queue import Queue, Empty
from threading import Thread, Event as ThreadEvent
from typing import Any, Dict, List

from utils.logger import get_logger
from config.constants import ENABLE_GUI_EVENTBUS

logger = get_logger(__name__)


class EventType(Enum):
    ENTRY_SIGNAL = "entry_signal"
    EXIT_SIGNAL = "exit_signal"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    PRICE_UPDATE = "price_update"
    ORDERBOOK_UPDATE = "orderbook_update"
    KLINE_UPDATE = "kline_update"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_LOST = "connection_lost"
    ERROR_OCCURRED = "error_occurred"
    SETTINGS_CHANGED = "settings_changed"
    TAB_SWITCHED = "tab_switched"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]
    source: str = ""
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EventHandler:
    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    def handle(self, event: Event) -> None:
        if self.enabled:
            self.process_event(event)

    def process_event(self, event: Event) -> None:
        pass


class EventBus:
    """이벤트 버스 (싱글톤)"""
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 이미 초기화되었으면 스킵
        if EventBus._initialized:
            return

        self.handlers: Dict[EventType, List[EventHandler]] = {}
        self.queue: Queue[Event] = Queue()
        self._stop = ThreadEvent()
        self.thread: Thread | None = None
        EventBus._initialized = True

    def subscribe(self, et, handler) -> None:
        """이벤트 구독 (EventType 또는 문자열 모두 지원)"""
        # 문자열이면 EventType으로 변환 시도
        if isinstance(et, str):
            try:
                et = EventType[et] if hasattr(EventType, et) else et
            except:
                pass  # 문자열 그대로 사용

        # handler가 함수면 EventHandler로 래핑
        if callable(handler) and not isinstance(handler, EventHandler):
            class SimpleHandler:
                def handle(self, event):
                    handler(event)
            handler = SimpleHandler()

        self.handlers.setdefault(et, []).append(handler)

    def publish(self, event: Event) -> None:
        if not self._stop.is_set():
            self.queue.put(event)
            # 동기 모드: 스레드가 시작되지 않았으면 즉시 처리
            if not self.thread or not self.thread.is_alive():
                self._process_event(event)

    def _process_event(self, event: Event) -> None:
        """이벤트 즉시 처리 (동기 모드)"""
        try:
            for h in self.handlers.get(event.type, []):
                h.handle(event)
        except Exception as e:
            logger.error(f"이벤트 처리 실패: {e}")

    def _loop(self):
        while not self._stop.is_set():
            try:
                ev = self.queue.get(timeout=0.5)
            except Empty:
                continue
            try:
                for h in self.handlers.get(ev.type, []):
                    h.handle(ev)
            except Exception as e:
                logger.error(f"이벤트 처리 실패: {e}")

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self._stop.clear()
        self.thread = Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info("이벤트 버스 시작")

    def stop(self):
        self._stop.set()
        logger.info("이벤트 버스 정지 요청")


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def publish_event(event_type: EventType, data: Dict[str, Any], source: str = "") -> None:
    get_event_bus().publish(Event(event_type, data, source))


def subscribe_to_event(event_type: EventType, handler: EventHandler) -> None:
    get_event_bus().subscribe(event_type, handler)


def start_event_system() -> None:
    get_event_bus().start()


def stop_event_system() -> None:
    get_event_bus().stop()


class GUIEventHandler(EventHandler):
    """선택적 GUI 핸들러: 가격 이벤트만 반영"""
    def __init__(self, main_window):
        super().__init__("GUIEventHandler")
        self.main_window = main_window

    def process_event(self, event: Event) -> None:
        if event.type is not EventType.PRICE_UPDATE:
            return
        try:
            data = event.data if isinstance(event.data, dict) else {}
            price = data.get("price")
            symbol = data.get("symbol", "BTCUSDT")
            if price is None or not hasattr(self.main_window, "price_label"):
                return
            base = symbol.replace("USDT", "") if isinstance(symbol, str) else str(symbol)
            self.main_window.price_label.setText(f"{base}: ${float(price):,.0f}")
            self.main_window.price_label.setToolTip("EventBus 가격 업데이트")
        except Exception as e:
            logger.error(f"가격 이벤트 처리 실패: {e}")

def register_gui_handler(main_window) -> None:
    """기능 플래그에 따라 GUI 핸들러를 등록"""
    try:
        if not ENABLE_GUI_EVENTBUS:
            return
        handler = GUIEventHandler(main_window)
        bus = get_event_bus()
        for et in (
            EventType.PRICE_UPDATE,
            EventType.POSITION_OPENED,
            EventType.POSITION_CLOSED,
            EventType.CONNECTION_ESTABLISHED,
            EventType.CONNECTION_LOST,
        ):
            bus.subscribe(et, handler)
        logger.info("GUIEventHandler 등록 완료 (EventBus 경로 활성)")
    except Exception as e:
        logger.error(f"GUI 핸들러 등록 실패: {e}")

