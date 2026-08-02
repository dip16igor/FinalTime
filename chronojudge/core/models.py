"""Модели данных для участников и результатов."""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional


@dataclass
class Participant:
    """Участник соревнования."""
    number: int
    full_name: str
    start_offset: Optional[timedelta] = None  # персональное смещение старта +MM:SS
    
    def __post_init__(self):
        if isinstance(self.start_offset, str):
            self.start_offset = parse_time_offset(self.start_offset)
    
    @property
    def has_personal_start(self) -> bool:
        return self.start_offset is not None


@dataclass
class FinishRecord:
    """Запись о финише участника."""
    participant: Participant
    timer_time: timedelta          # время таймера приложения на момент финиша
    manual_time: Optional[timedelta] = None  # ручное время судьи (секундомера)
    penalty_seconds: float = 0.0   # штрафные секунды (поле для будущего расчёта)
    penalty_points: int = 0        # штрафные баллы (поле для будущего расчёта)
    place: int = 0                 # место в отчёте (вычисляется при экспорте)
    final_time: Optional[timedelta] = None   # итоговое время (вычисляется)
    
    # Метаданные
    created_at: str = ""           # ISO timestamp
    is_edited: bool = False        # было ли ручное редактирование
    
    def __post_init__(self):
        if isinstance(self.timer_time, str):
            self.timer_time = parse_time_str(self.timer_time)
        if isinstance(self.manual_time, str) and self.manual_time:
            self.manual_time = parse_time_str(self.manual_time)
        if isinstance(self.penalty_seconds, str):
            self.penalty_seconds = float(self.penalty_seconds)
        if isinstance(self.penalty_points, str):
            self.penalty_points = int(self.penalty_points)


@dataclass
class CompetitionState:
    """Состояние соревнования (для сохранения/восстановления)."""
    registration_file: str = ""
    participants: list[Participant] = field(default_factory=list)
    finishes: list[FinishRecord] = field(default_factory=list)
    timer_elapsed: timedelta = timedelta(0)
    timer_running: bool = False
    common_start_offset: Optional[timedelta] = None
    pending_number: str = ""
    pending_manual_time: str = ""
    
    def __post_init__(self):
        if isinstance(self.timer_elapsed, str):
            self.timer_elapsed = parse_time_str(self.timer_elapsed)
        if isinstance(self.common_start_offset, str) and self.common_start_offset:
            self.common_start_offset = parse_time_str(self.common_start_offset)


def parse_time_str(time_str: str) -> timedelta:
    """Парсит строку времени в timedelta.
    
    Поддерживаемые форматы:
    - HH:MM:SS.sss
    - MM:SS.sss
    - SS.sss
    - HHH:MM:SS.sss (для ручного времени судьи)
    """
    time_str = time_str.strip()
    if not time_str:
        return timedelta(0)
    
    parts = time_str.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return timedelta(hours=int(h), minutes=int(m), seconds=float(s))
    elif len(parts) == 2:
        m, s = parts
        return timedelta(minutes=int(m), seconds=float(s))
    elif len(parts) == 1:
        return timedelta(seconds=float(parts[0]))
    else:
        raise ValueError(f"Неверный формат времени: {time_str}")


def parse_time_offset(offset_str: str) -> Optional[timedelta]:
    """Парсит смещение старта в формате +MM:SS или +MM:SS.sss."""
    offset_str = offset_str.strip()
    if not offset_str or offset_str.lower() in ("", "none", "null", "-"):
        return None
    
    if offset_str.startswith("+"):
        offset_str = offset_str[1:]
    
    return parse_time_str(offset_str)


def format_time(td: timedelta, show_hours: bool = True, precision: int = 1) -> str:
    """Форматирует timedelta в строку.
    
    Args:
        td: Временной интервал
        show_hours: Показывать часы всегда (даже если 0)
        precision: Количество знаков после запятой для секунд
    """
    total_seconds = td.total_seconds()
    if total_seconds < 0:
        sign = "-"
        total_seconds = -total_seconds
    else:
        sign = ""
    
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    
    if show_hours or hours > 0:
        return f"{sign}{hours:03d}:{minutes:02d}:{seconds:0{precision+3}.{precision}f}"
    else:
        return f"{sign}{minutes:02d}:{seconds:0{precision+3}.{precision}f}"


def format_time_short(td: timedelta, precision: int = 1) -> str:
    """Краткий формат: MM:SS.s или HH:MM:SS.s"""
    return format_time(td, show_hours=False, precision=precision)