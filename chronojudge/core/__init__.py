"""Core модуль: модели, таймер, калькулятор."""

from .models import (
    Participant,
    FinishRecord,
    CompetitionState,
    parse_time_str,
    parse_time_offset,
    format_time,
    format_time_short,
)
from .timer import AppTimer, TimerState
from .calculator import (
    calculate_final_time,
    calculate_all_results,
    get_participant_by_number,
    validate_number_input,
    validate_manual_time,
)

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