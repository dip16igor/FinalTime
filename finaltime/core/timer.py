"""Таймер приложения с точностью 0.1 сек."""

import time
from dataclasses import dataclass
from datetime import timedelta

from PySide6.QtCore import QObject, QTimer, Signal


@dataclass
class TimerState:
    """Состояние таймера (для сохранения/восстановления).

    Если running=True, точное прошедшее время вычисляется как:
        base_elapsed + (сейчас - started_at)
    где started_at — системное время (time.time()) момента старта.
    Это позволяет корректно восстановить таймер после краша приложения:
    время «тикает» и пока приложение было закрыто.
    """
    elapsed: timedelta = timedelta(0)       # зафиксированное прошедшее время
    running: bool = False
    base_elapsed: timedelta = timedelta(0)  # время до последнего старта
    started_at: float | None = None         # time.time() в момент старта


class AppTimer(QObject):
    """Таймер с сигналами для UI.

    Точность обновления: 100 мс (0.1 сек).
    Прошедшее время считается от системных часов (time.time()),
    а не накоплением тиков — поэтому оно точное даже после сна
    системы или восстановления после краша.
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

        self._elapsed = timedelta(0)        # текущее прошедшее время
        self._base_elapsed = timedelta(0)   # время на момент старта
        self._started_at: float | None = None  # системное время старта
        self._running = False

    @property
    def elapsed(self) -> timedelta:
        """Текущее прошедшее время (с точностью до системных часов)."""
        return self._compute_elapsed()

    @property
    def running(self) -> bool:
        return self._running

    def _compute_elapsed(self) -> timedelta:
        """Вычисляет прошедшее время от системных часов, если таймер идёт."""
        if self._running and self._started_at is not None:
            return self._base_elapsed + timedelta(
                seconds=max(time.time() - self._started_at, 0.0)
            )
        return self._elapsed

    def start(self) -> None:
        if not self._running:
            self._base_elapsed = self._elapsed
            self._started_at = time.time()
            self._running = True
            self._timer.start()
            self.started.emit()

    def stop(self) -> None:
        if self._running:
            self._elapsed = self._compute_elapsed()
            self._running = False
            self._started_at = None
            self._timer.stop()
            self.stopped.emit()

    def reset(self) -> None:
        was_running = self._running
        if was_running:
            self._timer.stop()
        self._elapsed = timedelta(0)
        self._base_elapsed = timedelta(0)
        self._started_at = None
        self._running = False
        self.tick.emit(self._elapsed)
        self.reset_requested.emit()
        if was_running:
            self.start()

    def set_elapsed(self, elapsed: timedelta) -> None:
        """Установить время таймера напрямую (для тестов/восстановления)."""
        self._elapsed = elapsed
        self._base_elapsed = elapsed
        self.tick.emit(self._elapsed)

    def _on_timeout(self) -> None:
        self._elapsed = self._compute_elapsed()
        self.tick.emit(self._elapsed)

    def get_state(self) -> TimerState:
        """Состояние для сохранения."""
        return TimerState(
            elapsed=self._compute_elapsed(),
            running=self._running,
            base_elapsed=self._base_elapsed,
            started_at=self._started_at,
        )

    def restore_state(self, state: TimerState) -> None:
        was_running = self._running
        self._running = state.running

        if state.running:
            if state.started_at is not None:
                # Таймер шёл: считаем реальное время от системных часов
                self._base_elapsed = state.base_elapsed
                self._started_at = state.started_at
                self._elapsed = self._compute_elapsed()
            else:
                # Старый формат (нет времени старта): продолжаем от значения
                self._base_elapsed = state.elapsed
                self._started_at = time.time()
                self._elapsed = state.elapsed
            self._timer.start()
            if not was_running:
                self.started.emit()
        else:
            self._elapsed = state.elapsed
            self._base_elapsed = state.elapsed
            self._started_at = None
            self._timer.stop()
            if was_running:
                self.stopped.emit()

        self.tick.emit(self._elapsed)
