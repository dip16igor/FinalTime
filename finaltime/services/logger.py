"""Централизованное логирование ошибок."""

import logging
import os
from pathlib import Path


class Logger:
    """Логгер с записью в файл и передачей в статус-бар."""

    def __init__(self, name: str = "FinalTime"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Избегаем дублирования хендлеров
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self) -> None:
        # Папка для логов
        if os.name == 'nt':
            appdata = os.environ.get('APPDATA')
            log_dir = Path(appdata) / "FinalTime" / "logs" if appdata else Path.cwd() / "data" / "logs"
        else:
            log_dir = Path.cwd() / "data" / "logs"

        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "finaltime.log"

        # Файловый хендлер с ротацией (простая - перезапись при запуске)
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # Формат: timestamp | level | source | message
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

        # Консольный хендлер для отладки
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def log(self, level: str, message: str, source: str = "") -> None:
        """Записать сообщение в лог.

        Args:
            level: DEBUG, INFO, WARNING, ERROR, CRITICAL
            message: Текст сообщения
            source: Источник (модуль, функция)
        """
        full_message = f"{source} | {message}" if source else message

        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        log_level = level_map.get(level.upper(), logging.INFO)
        self.logger.log(log_level, full_message)

    def debug(self, message: str, source: str = "") -> None:
        self.log("DEBUG", message, source)

    def info(self, message: str, source: str = "") -> None:
        self.log("INFO", message, source)

    def warning(self, message: str, source: str = "") -> None:
        self.log("WARNING", message, source)

    def error(self, message: str, source: str = "", exc_info: bool = False) -> None:
        self.log("ERROR", message, source)
        if exc_info:
            self.logger.exception(message)

    def critical(self, message: str, source: str = "") -> None:
        self.log("CRITICAL", message, source)

    def close(self) -> None:
        """Закрыть все хендлеры."""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
