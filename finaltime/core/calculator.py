"""Логика расчёта итоговых времён."""

from datetime import timedelta

from .models import FinishRecord, Participant


def calculate_final_time(
    record: FinishRecord,
    common_start: timedelta | None = None
) -> timedelta:
    """Вычисляет итоговое время участника.

    Правила:
    1. Базовое время = manual_time (если задано) ИЛИ timer_time
    2. Вычитаем стартовое смещение:
       - Если у участника есть персональный старт (participant.start_offset), используем его
       - Иначе используем общий старт (common_start)
       - Если старт не задан, вычитаем 0
    3. Результат не может быть отрицательным (минимум 0)

    Штрафы (penalty_seconds, penalty_points) сохраняются как поля,
    но НЕ применяются к времени в текущей версии.
    """
    # Базовое время финиша
    base_time = record.manual_time if record.manual_time is not None else record.timer_time

    # Определяем смещение старта
    participant = record.participant
    start_offset = timedelta(0)

    if participant.has_personal_start and participant.start_offset is not None:
        start_offset = participant.start_offset
    elif common_start is not None:
        start_offset = common_start

    # Итоговое время = базовое - старт
    final = base_time - start_offset

    # Не допускаем отрицательного времени
    return max(final, timedelta(0))



def calculate_all_results(
    finishes: list[FinishRecord],
    common_start: timedelta | None = None
) -> list[FinishRecord]:
    """Вычисляет итоговые времена для всех записей и сортирует по месту."""
    # Считаем время для каждой записи
    for record in finishes:
        record.final_time = calculate_final_time(record, common_start)

    # Сортируем по итоговому времени (возрастание)
    sorted_finishes = sorted(
        finishes,
        key=lambda r: r.final_time or timedelta.max
    )

    # Назначаем места
    for i, record in enumerate(sorted_finishes, 1):
        record.place = i

    return sorted_finishes


def get_participant_by_number(
    participants: list[Participant],
    number: int
) -> Participant | None:
    """Поиск участника по номеру."""
    for p in participants:
        if p.number == number:
            return p
    return None


def validate_number_input(text: str) -> int | None:
    """Валидация ввода номера (только цифры)."""
    text = text.strip()
    if not text:
        return None
    if not text.isdigit():
        return None
    num = int(text)
    if num <= 0:
        return None
    return num


def validate_manual_time(text: str) -> timedelta | None:
    """Валидация ручного времени в формате HHH:MM:SS.sss."""
    text = text.strip()
    if not text:
        return None

    # Проверяем формат
    parts = text.split(":")
    if len(parts) != 3:
        return None

    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])

        if hours < 0 or minutes < 0 or minutes >= 60 or seconds < 0 or seconds >= 60:
            return None

        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    except ValueError:
        return None
