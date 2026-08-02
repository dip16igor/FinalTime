"""Управление сессией приложения."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from chronojudge.services.logger import Logger


class SessionManager:
    """Управление сессией: метаданные, запуск, завершение."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.start_time = datetime.now()
        self.session_id = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.registration_file: Optional[str] = None
        self.finishes_count = 0
        
        self.logger.info(f"Сессия начата: {self.session_id}")
    
    def set_registration_file(self, file_path: str) -> None:
        self.registration_file = file_path
        self.logger.info(f"Файл регистрации: {file_path}")
    
    def increment_finishes(self) -> int:
        self.finishes_count += 1
        return self.finishes_count
    
    def get_summary(self) -> dict:
        """Сводка по сессии."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "registration_file": self.registration_file,
            "finishes_count": self.finishes_count,
        }
    
    def end_session(self) -> None:
        self.logger.info(f"Сессия завершена: {self.session_id}, финишей: {self.finishes_count}")