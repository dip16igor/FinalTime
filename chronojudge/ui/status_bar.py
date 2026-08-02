"""Статусная строка приложения."""

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QStatusBar, QLabel, QWidget, QHBoxLayout


class StatusBar(QStatusBar):
    """Статусная строка с временными и постоянными сообщениями."""
    
    # Сигнал для логирования ошибок
    error_logged = Signal(str, str)  # level, message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Основная метка состояния
        self._status_label = QLabel("Готово")
        self._status_label.setMinimumWidth(200)
        self.addWidget(self._status_label, 1)
        
        # Метка для дополнительной информации (версия, файл и т.д.)
        self._info_label = QLabel("")
        self.addPermanentWidget(self._info_label)
        
        # Таймер для автоочистки временных сообщений
        self._clear_timer = QTimer(self)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._clear_temporary)
        
        self._permanent_message = "Готово"
    
    def show_message(self, message: str, timeout: int = 0) -> None:
        """Показать сообщение.
        
        Args:
            message: Текст сообщения
            timeout: Время в мс, после которого сообщение сбросится на постоянное.
                     0 = не сбрасывать автоматически.
        """
        self._status_label.setText(message)
        if timeout > 0:
            self._clear_timer.start(timeout)
    
    def show_error(self, message: str, timeout: int = 5000) -> None:
        """Показать ошибку (красным) и залогировать."""
        self._status_label.setText(f"Ошибка: {message}")
        self._status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        self.error_logged.emit("ERROR", message)
        if timeout > 0:
            self._clear_timer.start(timeout)
    
    def show_warning(self, message: str, timeout: int = 3000) -> None:
        """Показать предупреждение (оранжевым)."""
        self._status_label.setText(f"Предупреждение: {message}")
        self._status_label.setStyleSheet("color: #ffaa00;")
        self.error_logged.emit("WARNING", message)
        if timeout > 0:
            self._clear_timer.start(timeout)
    
    def show_info(self, message: str, timeout: int = 3000) -> None:
        """Показать информацию (синим)."""
        self._status_label.setText(message)
        self._status_label.setStyleSheet("color: #4488ff;")
        if timeout > 0:
            self._clear_timer.start(timeout)
    
    def set_permanent(self, message: str) -> None:
        """Установить постоянное сообщение (базовое состояние)."""
        self._permanent_message = message
        self._status_label.setText(message)
        self._status_label.setStyleSheet("")
        self._clear_timer.stop()
    
    def set_info_text(self, text: str) -> None:
        """Установить дополнительную информацию (справа)."""
        self._info_label.setText(text)
    
    def _clear_temporary(self) -> None:
        """Вернуться к постоянному сообщению."""
        self._status_label.setText(self._permanent_message)
        self._status_label.setStyleSheet("")
    
    def clear(self) -> None:
        """Очистить к базовому состоянию."""
        self.set_permanent("Готово")