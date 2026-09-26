"""Core модуль: модели, таймер, калькулятор."""

from .calculator import (
    calculate_all_results,
    calculate_final_time,
    format_gap,
    gaps_to_leader,
    get_participant_by_number,
    validate_manual_time,
    validate_number_input,
)
from .models import (
    AgeCategory,
    CompetitionState,
    FinishRecord,
    Gender,
    Participant,
    format_time,
    format_time_short,
    parse_date,
    parse_time_offset,
    parse_time_str,
)
from .timer import AppTimer, TimerState

__all__ = [
    "AgeCategory",
    "CompetitionState",
    "FinishRecord",
    "Gender",
    "Participant",
    "parse_time_str",
    "parse_time_offset",
    "parse_date",
    "format_time",
    "format_time_short",
    "AppTimer",
    "TimerState",
    "calculate_final_time",
    "calculate_all_results",
    "format_gap",
    "gaps_to_leader",
    "validate_number_input",
    "validate_manual_time",
]
