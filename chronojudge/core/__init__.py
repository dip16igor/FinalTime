"""Core модуль: модели, таймер, калькулятор."""

from .calculator import (
    calculate_all_results,
    calculate_final_time,
    get_participant_by_number,
    validate_manual_time,
    validate_number_input,
)
from .models import (
    CompetitionState,
    FinishRecord,
    Participant,
    format_time,
    format_time_short,
    parse_time_offset,
    parse_time_str,
)
from .timer import AppTimer, TimerState

__all__ = [
    "Participant",
    "FinishRecord",
    "CompetitionState",
    "parse_time_str",
    "parse_time_offset",
    "format_time",
    "format_time_short",
    "AppTimer",
    "TimerState",
    "calculate_final_time",
    "calculate_all_results",
    "get_participant_by_number",
    "validate_number_input",
    "validate_manual_time",
]
