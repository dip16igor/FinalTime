"""Пользовательские виджеты для ввода и отображения."""

from datetime import date, timedelta

from PySide6.QtCore import QElapsedTimer, QRegularExpression, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPainterPath, QPen, QPolygonF, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from finaltime.core import AgeCategory, format_time_short


class HoldButton(QPushButton):
    """Кнопка, срабатывающая только при долгом удержании.

    При удержании левой кнопки мыши по периметру кнопки рисуется
    линия, которая уменьшается. Когда линия исчезает (через 3 сек),
    кнопка срабатывает (сигнал hold_activated). Если отпустить раньше —
    срабатывание отменяется.
    """

    hold_activated = Signal()

    HOLD_TIMEOUT_MS = 3000      # 3 секунды
    TICK_INTERVAL_MS = 30       # обновление прогресса
    RING_WIDTH = 4              # толщина линии по периметру
    RING_RADIUS = 6             # радиус скругления углов кнопки (QSS border-radius)
    RING_INSET = 2              # отступ линии от края кнопки

    def __init__(self, text: str = "", ring_color: str = "#ffffff", parent=None):
        super().__init__(text, parent)
        self._ring_color = QColor(ring_color)
        self._progress = 0.0          # 1.0 = полная линия, 0.0 = срабатывание
        self._holding = False
        self._hold_start = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_INTERVAL_MS)
        self._timer.timeout.connect(self._on_tick)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Удерживайте 3 секунды для подтверждения")

    # === Управление удержанием ===

    def _start_hold(self) -> None:
        self._holding = True
        self._progress = 1.0
        self._hold_start.start()
        self.setDown(True)
        self._timer.start()
        self.update()

    def _cancel_hold(self) -> None:
        self._holding = False
        self._timer.stop()
        self._progress = 0.0
        self.setDown(False)
        self.update()

    def _complete_hold(self) -> None:
        self._timer.stop()
        self._holding = False
        self._progress = 0.0
        self.setDown(False)
        self.update()
        self.hold_activated.emit()

    def _on_tick(self) -> None:
        # Прогресс считаем от реально прошедшего времени, а не от количества
        # тиков: Qt сливает таймерные события, если очередь занята отрисовкой,
        # из-за чего фиксированное уменьшение за тик замедляло анимацию вдвое.
        elapsed_ms = self._hold_start.elapsed()
        self._progress = max(1.0 - elapsed_ms / self.HOLD_TIMEOUT_MS, 0.0)
        if elapsed_ms >= self.HOLD_TIMEOUT_MS:
            self._complete_hold()
        else:
            self.update()

    # === События мыши ===

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self._start_hold()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._holding:
            self._cancel_hold()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseLeaveEvent(self, event) -> None:
        if self._holding:
            self._cancel_hold()
        super().mouseLeaveEvent(event)

    # === Отрисовка линии прогресса ===

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._holding or self._progress <= 0.0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Линия идёт по периметру с отступом RING_INSET от края кнопки.
        # Радиус скругления линии должен быть меньше радиуса кнопки на
        # величину отступа, иначе углы линии не совпадут с углами кнопки.
        rect = self.rect().adjusted(
            self.RING_INSET, self.RING_INSET,
            -self.RING_INSET, -self.RING_INSET,
        )
        radius = max(self.RING_RADIUS - self.RING_INSET, 1)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        # Рисуем линию по периметру, уменьшающуюся при удержании.
        # Используем pointAtPercent + polyline, т.к. dash-паттерн Qt
        # не уменьшает линию плавно на QPainterPath.
        total_len = path.length()
        target_len = total_len * self._progress
        end_t = path.percentAtLength(target_len)
        steps = max(int(target_len), 1)

        poly = QPolygonF()
        for i in range(steps + 1):
            t = end_t * i / steps
            poly.append(path.pointAtPercent(t))

        pen = QPen(self._ring_color, self.RING_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPolyline(poly)
        painter.end()


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
        ("ФИО", 220, False),
        ("Категория", 80, False),  # Новая колонка
        ("Время таймера", 110, False),
        ("Ручное время", 110, True),
        ("Штраф (с)", 70, True),
        ("Штраф (баллы)", 80, True),
        ("Итоговое время", 120, False),
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

    def add_result(
        self,
        record,
        place: int,
        competition_date: date | None = None,
        categories: list[AgeCategory] | None = None
    ) -> int:
        """Добавить запись результата в таблицу."""
        row = self.rowCount()
        self.insertRow(row)

        timer_str = format_time_short(record.timer_time)
        manual_str = format_time_short(record.manual_time) if record.manual_time else ""
        final_str = format_time_short(record.final_time) if record.final_time else ""

        # Категория
        category_str = "-"
        if competition_date and categories and record.participant.date_of_birth:
            category_str = record.participant.category_label(competition_date, categories)

        items_data = [
            (str(place), False),
            (str(record.participant.number), True),
            (record.participant.full_name, False),
            (category_str, False),  # Категория
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

    def update_row(
        self,
        row: int,
        record,
        place: int,
        competition_date: date | None = None,
        categories: list[AgeCategory] | None = None
    ) -> None:
        """Обновить существующую строку."""
        timer_str = format_time_short(record.timer_time)
        manual_str = format_time_short(record.manual_time) if record.manual_time else ""
        final_str = format_time_short(record.final_time) if record.final_time else ""

        category_str = "-"
        if competition_date and categories and record.participant.date_of_birth:
            category_str = record.participant.category_label(competition_date, categories)

        data = [
            str(place),
            str(record.participant.number),
            record.participant.full_name,
            category_str,
            timer_str,
            manual_str,
            str(record.penalty_seconds),
            str(record.penalty_points),
            final_str,
        ]

        for col, text in enumerate(data):
            item = self.item(row, col)
            if item:
                self.blockSignals(True)
                item.setText(text)
                self.blockSignals(False)

    def get_row_data(self, row: int) -> dict:
        """Получить данные строки как словарь."""
        return {
            "place": self.item(row, 0).text() if self.item(row, 0) else "",
            "number": self.item(row, 1).text() if self.item(row, 1) else "",
            "name": self.item(row, 2).text() if self.item(row, 2) else "",
            "category": self.item(row, 3).text() if self.item(row, 3) else "",
            "timer_time": self.item(row, 4).text() if self.item(row, 4) else "",
            "manual_time": self.item(row, 5).text() if self.item(row, 5) else "",
            "penalty_seconds": self.item(row, 6).text() if self.item(row, 6) else "0",
            "penalty_points": self.item(row, 7).text() if self.item(row, 7) else "0",
            "final_time": self.item(row, 8).text() if self.item(row, 8) else "",
        }