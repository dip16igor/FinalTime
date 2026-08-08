"""Таймер приложения с точностью 0.1 сек."""

from dataclasses import dataclass
from datetime import timedelta

from PySide6.QtCore import QObject, QTimer, Signal


@dataclass
class TimerState:
    """Состояние таймера."""
    elapsed: timedelta = timedelta(0)
    running: bool = False


class AppTimer(QObject):
    """Таймер с сигналами для UI.

    Точность обновления: 100 мс (0.1 сек).
    """
    tick = Signal(timedelta)      # текущее прошедшее время
    started = Signal()
    stopped = Signal()
    reset_requested = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(100)  # 100 мс = 0.1 сек
        self._timer.timeout.connect(self._on_timeout)

        self._elapsed = timedelta(0)
        self._running = False

    @property
    def elapsed(self) -> timedelta:
        return self._elapsed

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._timer.start()
            self.started.emit()

    def stop(self) -> None:
        if self._running:
            self._running = False
            self._timer.stop()
            self.stopped.emit()

    def reset(self) -> None:
        was_running = self._running
        if was_running:
            self._timer.stop()
        self._elapsed = timedelta(0)
        self._running = False
        self.tick.emit(self._elapsed)
        self.reset_requested.emit()
        if was_running:
            self.start()

    def set_elapsed(self, elapsed: timedelta) -> None:
        """Установить время таймера (для восстановления состояния)."""
        self._elapsed = elapsed
        self.tick.emit(self._elapsed)

    def _on_timeout(self) -> None:
        self._elapsed += timedelta(milliseconds=100)
        self.tick.emit(self._elapsed)

    def get_state(self) -> TimerState:
        return TimerState(elapsed=self._elapsed, running=self._running)

    def restore_state(self, state: TimerState) -> None:
        self._elapsed = state.elapsed
        was_running = self._running
        self._running = state.running
        self.tick.emit(self._elapsed)
        if self._running:
            self._timer.start()
            if not was_running:
                self.started.emit()
        else:
            self._timer.stop()
            if was_running:
                self.stopped.emit()
