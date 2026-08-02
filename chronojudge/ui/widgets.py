"""Пользовательские виджеты для ввода и отображения."""

from datetime import timedelta

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QKeyEvent, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLineEdit,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
)


class NumberLineEdit(QLineEdit):
    """Поле ввода только для цифр (номер участника)."""

    finish_requested = Signal()  # Enter нажат

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Номер участника")
        self.setMaxLength(6)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Валидатор: только цифры
        validator = QRegularExpressionValidator(QRegularExpression(r"[0-9]*"), self)
        self.setValidator(validator)

        # Стиль
        self.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                padding: 8px;
                border: 2px solid #ccc;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-color: #4a90d9;
            }
        """)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.finish_requested.emit()
            # Enter не должен переводить фокус на следующее поле
            # Tab делает это, Enter - только финиш
            self.setFocus()
            event.accept()
        else:
            super().keyPressEvent(event)

    def get_number(self) -> int | None:
        text = self.text().strip()
        if text.isdigit():
            return int(text)
        return None

    def clear_input(self) -> None:
        self.clear()
        self.setFocus()


class ManualTimeLineEdit(QLineEdit):
    """Поле ввода ручного времени в формате HHH:MM:SS.sss."""

    finish_requested = Signal()  # Enter нажат

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("HHH:MM:SS.sss")
        self.setMaxLength(13)  # HHH:MM:SS.sss
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setInputMask("999:99:99.999")

        self.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                font-family: 'Consolas', 'Monospace';
                padding: 8px;
                border: 2px solid #ccc;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-color: #4a90d9;
            }
        """)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.finish_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def get_time(self) -> timedelta | None:
        text = self.text().strip()
        if not text or text == "000:00:00.000":
            return None

        try:
            parts = text.split(":")
            if len(parts) != 3:
                return None
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])

            if minutes >= 60 or seconds >= 60:
                return None

            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        except ValueError:
            return None

    def set_time(self, td: timedelta) -> None:
        total = td.total_seconds()
        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)
        seconds = total % 60
        self.setText(f"{hours:03d}:{minutes:02d}:{seconds:06.3f}")

    def clear_input(self) -> None:
        self.clear()
        self.setFocus()


class EditableTableWidgetItem(QTableWidgetItem):
    """Ячейка таблицы, редактируемая по двойному клику."""

    def __init__(self, text: str = "", editable: bool = True):
        super().__init__(text)
        if not editable:
            # Используем базовые флаги без ItemIsEditable, чтобы избежать рекурсии self.flags()
            self.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)


class ResultsTable(QTableWidget):
    """Таблица результатов с редактированием по двойному клику."""

    COLUMNS = [
        ("Место", 60, False),
        ("Номер", 80, True),
        ("ФИО", 250, False),
        ("Время таймера", 120, False),
        ("Ручное время", 120, True),
        ("Штраф (с)", 80, True),
        ("Штраф (баллы)", 90, True),
        ("Итоговое время", 130, False),
    ]

    cell_changed = Signal(int, int, str)  # row, col, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_table()
        self.itemChanged.connect(self._on_item_changed)

    def _setup_table(self) -> None:
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels([c[0] for c in self.COLUMNS])

        header = self.horizontalHeader()
        for i, (_, width, _) in enumerate(self.COLUMNS):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(i, width)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Стиль
        self.setStyleSheet("""
            QTableWidget {
                font-size: 13px;
                gridline-color: #ddd;
                alternate-background-color: #f9f9f9;
            }
            QHeaderView::section {
                background-color: #e8e8e8;
                padding: 6px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #d0e8ff;
            }
        """)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        self.cell_changed.emit(item.row(), item.column(), item.text())

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        delete_action = menu.addAction("Удалить запись")
        action = menu.exec(self.viewport().mapToGlobal(pos))
        if action == delete_action:
            self.removeRow(self.currentRow())

    def add_result(self, record, place: int) -> int:
        """Добавить запись результата в таблицу."""
        row = self.rowCount()
        self.insertRow(row)

        # Форматируем времена
        from chronojudge.core import format_time_short

        timer_str = format_time_short(record.timer_time)
        manual_str = format_time_short(record.manual_time) if record.manual_time else ""
        final_str = format_time_short(record.final_time) if record.final_time else ""

        items_data = [
            (str(place), False),
            (str(record.participant.number), True),
            (record.participant.full_name, False),
            (timer_str, False),
            (manual_str, True),
            (str(record.penalty_seconds), True),
            (str(record.penalty_points), True),
            (final_str, False),
        ]

        for col, (text, editable) in enumerate(items_data):
            item = EditableTableWidgetItem(text, editable)
            self.setItem(row, col, item)

        return row

    def update_row(self, row: int, record, place: int) -> None:
        """Обновить существующую строку."""
        from chronojudge.core import format_time_short

        timer_str = format_time_short(record.timer_time)
        manual_str = format_time_short(record.manual_time) if record.manual_time else ""
        final_str = format_time_short(record.final_time) if record.final_time else ""

        data = [
            str(place),
            str(record.participant.number),
            record.participant.full_name,
            timer_str,
            manual_str,
            str(record.penalty_seconds),
            str(record.penalty_points),
            final_str,
        ]

        for col, text in enumerate(data):
            item = self.item(row, col)
            if item:
                # Блокируем сигналы во время программного обновления
                self.blockSignals(True)
                item.setText(text)
                self.blockSignals(False)

    def get_row_data(self, row: int) -> dict:
        """Получить данные строки как словарь."""
        return {
            "place": self.item(row, 0).text() if self.item(row, 0) else "",
            "number": self.item(row, 1).text() if self.item(row, 1) else "",
            "name": self.item(row, 2).text() if self.item(row, 2) else "",
            "timer_time": self.item(row, 3).text() if self.item(row, 3) else "",
            "manual_time": self.item(row, 4).text() if self.item(row, 4) else "",
            "penalty_seconds": self.item(row, 5).text() if self.item(row, 5) else "0",
            "penalty_points": self.item(row, 6).text() if self.item(row, 6) else "0",
            "final_time": self.item(row, 7).text() if self.item(row, 7) else "",
        }
