"""Сохранение и восстановление промежуточного состояния."""

import json
import os
from pathlib import Path

from finaltime.core import (
    CompetitionState,
    FinishRecord,
    Gender,
    Participant,
    format_time_short,
    parse_date,
    parse_time_str,
)


class StateManager:
    """Управление сохранением/восстановлением состояния приложения."""

    def __init__(self, logger):
        self.logger = logger
        self.data_dir = self._get_data_dir()
        self.state_file = self.data_dir / "state.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_data_dir(self) -> Path:
        """Папка для данных: %APPDATA%/FinalTime/ или ./data/"""
        if os.name == 'nt':
            appdata = os.environ.get('APPDATA')
            if appdata:
                return Path(appdata) / "FinalTime"
        return Path.cwd() / "data"

    def save(self, state: CompetitionState) -> None:
        """Сохранить состояние в JSON."""
        try:
            data = {
                "competition_name": state.competition_name,
                "registration_file": state.registration_file,
                "categories_file": state.categories_file,
                "competition_date": state.competition_date,
                "participants": [
                    {
                        "number": p.number,
                        "full_name": p.full_name,
                        "start_offset": format_time_short(p.start_offset) if p.start_offset else None,
                        "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
                        "gender": p.gender.value,
                    }
                    for p in state.participants
                ],
                "finishes": [
                    {
                        "participant_number": r.participant.number,
                        "timer_time": format_time_short(r.timer_time),
                        "manual_time": format_time_short(r.manual_time) if r.manual_time else None,
                        "penalty_seconds": r.penalty_seconds,
                        "penalty_points": r.penalty_points,
                        "place": r.place,
                        "final_time": format_time_short(r.final_time) if r.final_time else None,
                        "created_at": r.created_at,
                        "is_edited": r.is_edited,
                    }
                    for r in state.finishes
                ],
                "timer_elapsed": format_time_short(state.timer_elapsed),
                "timer_running": state.timer_running,
                "timer_base_elapsed": state.timer_base_elapsed,
                "timer_started_at": state.timer_started_at,
                "common_start_offset": format_time_short(state.common_start_offset) if state.common_start_offset else None,
                "pending_number": state.pending_number,
                "pending_manual_time": state.pending_manual_time,
            }

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.log("DEBUG", f"State saved: {self.state_file}")

        except Exception as e:
            self.logger.log("ERROR", f"Error saving state: {e}")

    def load(self) -> CompetitionState | None:
        """Загрузить состояние из JSON."""
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, encoding='utf-8') as f:
                data = json.load(f)

            # Участники
            participants = []
            for p_data in data.get("participants", []):
                start_offset = None
                if p_data.get("start_offset"):
                    start_offset = parse_time_str(p_data["start_offset"])
                date_of_birth = None
                if p_data.get("date_of_birth"):
                    try:
                        date_of_birth = parse_date(p_data["date_of_birth"])
                    except ValueError:
                        date_of_birth = None
                participants.append(Participant(
                    number=p_data["number"],
                    full_name=p_data["full_name"],
                    start_offset=start_offset,
                    date_of_birth=date_of_birth,
                    gender=Gender.from_string(p_data.get("gender", "")),
                ))

            # Финиши - нужно восстановить ссылки на участников
            finishes = []
            for f_data in data.get("finishes", []):
                # Ищем участника по номеру
                participant = None
                for p in participants:
                    if p.number == f_data["participant_number"]:
                        participant = p
                        break

                if participant is None:
                    self.logger.log("WARNING", f"Участник #{f_data['participant_number']} не найден при восстановлении")
                    continue

                timer_time = parse_time_str(f_data["timer_time"])
                manual_time = None
                if f_data.get("manual_time"):
                    manual_time = parse_time_str(f_data["manual_time"])
                final_time = None
                if f_data.get("final_time"):
                    final_time = parse_time_str(f_data["final_time"])

                finishes.append(FinishRecord(
                    participant=participant,
                    timer_time=timer_time,
                    manual_time=manual_time,
                    penalty_seconds=f_data.get("penalty_seconds", 0.0),
                    penalty_points=f_data.get("penalty_points", 0),
                    place=f_data.get("place", 0),
                    final_time=final_time,
                    created_at=f_data.get("created_at", ""),
                    is_edited=f_data.get("is_edited", False),
                ))

            timer_elapsed = parse_time_str(data.get("timer_elapsed", "0"))
            timer_running = data.get("timer_running", False)
            timer_base_elapsed = data.get("timer_base_elapsed", "")
            timer_started_at = data.get("timer_started_at")
            common_start = None
            if data.get("common_start_offset"):
                common_start = parse_time_str(data["common_start_offset"])

            state = CompetitionState(
                competition_name=data.get("competition_name", ""),
                registration_file=data.get("registration_file", ""),
                categories_file=data.get("categories_file", ""),
                competition_date=data.get("competition_date", ""),
                participants=participants,
                finishes=finishes,
                timer_elapsed=timer_elapsed,
                timer_running=timer_running,
                timer_base_elapsed=timer_base_elapsed,
                timer_started_at=timer_started_at,
                common_start_offset=common_start,
                pending_number=data.get("pending_number", ""),
                pending_manual_time=data.get("pending_manual_time", ""),
            )

            self.logger.log("INFO", f"State restored: {len(participants)} participants, {len(finishes)} finishes")
            return state

        except Exception as e:
            self.logger.log("ERROR", f"Error loading state: {e}")
            return None

    def clear(self) -> None:
        """Delete saved state."""
        if self.state_file.exists():
            self.state_file.unlink()
            self.logger.log("INFO", "Saved state cleared")
