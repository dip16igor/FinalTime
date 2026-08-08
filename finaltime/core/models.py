"""Модели данных для участников и результатов."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional


class Gender(str, Enum):
    """Пол участника."""
    MALE = "М"
    FEMALE = "Ж"
    UNKNOWN = "-"

    @classmethod
    def from_string(cls, value: str) -> "Gender":
        """Парсит пол из строки."""
        if not value:
            return cls.UNKNOWN
        v = value.strip().upper()
        if v in ("М", "МУЖ", "MALE", "M", "МУЖЧИНА"):
            return cls.MALE
        if v in ("Ж", "ЖЕН", "FEMALE", "F", "ЖЕНЩИНА"):
            return cls.FEMALE
        return cls.UNKNOWN


@dataclass
class AgeCategory:
    """Возрастная категория."""
    name: str                    # например: "Мужчины 18-25"
    gender: Gender               # пол категории
    min_age: int                 # минимальный возраст (включительно)
    max_age: int                 # максимальный возраст (включительно), 999 = нет ограничения
    is_open: bool = False        # общий зачёт (например "Общий зачёт женщины")

    def matches(self, gender: Gender, age: int) -> bool:
        """Проверяет, подходит ли участник под категорию."""
        if self.is_open:
            return gender == self.gender
        return gender == self.gender and self.min_age <= age <= self.max_age

    def short_label(self) -> str:
        """Краткий ярлык для GUI: М40, Ж25 и т.д."""
        if self.is_open:
            return f"{self.gender.value}Общ"
        if self.min_age == self.max_age:
            return f"{self.gender.value}{self.min_age}"
        return f"{self.gender.value}{self.min_age}-{self.max_age}"


@dataclass
class Participant:
    """Участник соревнования."""
    number: int
    full_name: str
    start_offset: timedelta | None = None      # персональное смещение старта +MM:SS
    date_of_birth: date | None = None          # дата рождения
    gender: Gender = Gender.UNKNOWN            # пол

    def __post_init__(self):
        if isinstance(self.start_offset, str):
            self.start_offset = parse_time_offset(self.start_offset)
        if isinstance(self.date_of_birth, str):
            self.date_of_birth = parse_date(self.date_of_birth)
        if isinstance(self.gender, str):
            self.gender = Gender.from_string(self.gender)

    @property
    def has_personal_start(self) -> bool:
        return self.start_offset is not None

    def age_on_date(self, competition_date: date) -> int | None:
        """Возвращает количество полных лет на дату соревнований."""
        if self.date_of_birth is None:
            return None
        age = competition_date.year - self.date_of_birth.year
        # Если день рождения ещё не наступил в году соревнований
        if (competition_date.month, competition_date.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return max(0, age)

    def category_label(self, competition_date: date, categories: list["AgeCategory"]) -> str:
        """Возвращает ярлык категории для GUI (например М40, Ж25)."""
        age = self.age_on_date(competition_date)
        if age is None:
            return "-"
        for cat in categories:
            if cat.matches(self.gender, age):
                return cat.short_label()
        return f"{self.gender.value}{age}"


@dataclass
class FinishRecord:
    """Запись о финише участника."""
    participant: Participant
    timer_time: timedelta          # время таймера приложения на момент финиша
    manual_time: timedelta | None = None  # ручное время судьи (секундомера)
    penalty_seconds: float = 0.0   # штрафные секунды (поле для будущего расчёта)
    penalty_points: int = 0        # штрафные баллы (поле для будущего расчёта)
    place: int = 0                 # место в отчёте (вычисляется при экспорте)
    final_time: timedelta | None = None   # итоговое время (вычисляется)
    sequence: int = 0              # порядок нажатия Finish! (1, 2, 3...)

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
    categories_file: str = ""
    competition_date: str = ""
    participants: list[Participant] = field(default_factory=list)
    finishes: list[FinishRecord] = field(default_factory=list)
    timer_elapsed: timedelta = timedelta(0)
    timer_running: bool = False
    common_start_offset: timedelta | None = None
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
    if len(parts) == 2:
        m, s = parts
        return timedelta(minutes=int(m), seconds=float(s))
    if len(parts) == 1:
        return timedelta(seconds=float(parts[0]))
    raise ValueError(f"Неверный формат времени: {time_str}")


def parse_time_offset(offset_str: str) -> timedelta | None:
    """Парсит смещение старта в формате +MM:SS или +MM:SS.sss."""
    offset_str = offset_str.strip()
    if not offset_str or offset_str.lower() in ("", "none", "null", "-"):
        return None

    offset_str = offset_str.removeprefix("+")

    return parse_time_str(offset_str)


def parse_date(date_str: str) -> date | None:
    """Парсит дату в формате DD.MM.YYYY или YYYY-MM-DD."""
    date_str = date_str.strip()
    if not date_str or date_str.lower() in ("", "none", "null", "-"):
        return None

    # Пробуем разные форматы
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%y"):
        try:
            return date.fromisoformat(date_str) if fmt == "%Y-%m-%d" else date.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Неверный формат даты: {date_str} (ожидается DD.MM.YYYY)")


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
    return f"{sign}{minutes:02d}:{seconds:0{precision+3}.{precision}f}"


def format_time_short(td: timedelta, precision: int = 1) -> str:
    """Краткий формат: MM:SS.s или HH:MM:SS.s"""
    return format_time(td, show_hours=False, precision=precision)