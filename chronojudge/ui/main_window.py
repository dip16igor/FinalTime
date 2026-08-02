"""Главное окно приложения."""

import sys
from datetime import timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chronojudge import get_app_title, get_version
from chronojudge.core import (
    AppTimer,
    CompetitionState,
    FinishRecord,
    Participant,
    TimerState,
    calculate_all_results,
    format_time_short,
    get_participant_by_number,
    validate_manual_time,
)
from chronojudge.io import ExcelImporter, Exporter, StateManager
from chronojudge.services import Logger, SessionManager
from chronojudge.ui.status_bar import StatusBar
from chronojudge.ui.widgets import ManualTimeLineEdit, NumberLineEdit, ResultsTable


class MainWindow(QMainWindow):
    """Главное окно приложения ChronoJudge."""

    def __init__(self):
        super().__init__()

        # Версия в заголовке
        self.setWindowTitle(get_app_title())
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)

        # Сервисы
        self.logger = Logger()
        self.session = SessionManager(self.logger)
        self.state_manager = StateManager(self.logger)
        self.excel_importer = ExcelImporter(self.logger)
        self.exporter = Exporter(self.logger)

        # Данные
        self.participants: list[Participant] = []
        self.finishes: list[FinishRecord] = []
        self.common_start: timedelta | None = None
        self.registration_file: str = ""

        # Таймер
        self.timer = AppTimer(self)
        self.timer.tick.connect(self._on_timer_tick)
        self.timer.started.connect(lambda: self._update_timer_buttons(running=True))
        self.timer.stopped.connect(lambda: self._update_timer_buttons(running=False))

        # UI
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_menu()

        # Восстановление состояния
        self._restore_state()

        # Автосохранение каждые 30 сек
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 10)

        # === ВЕРХНЯЯ ЧАСТЬ: ТАЙМЕР ===
        timer_group = QGroupBox("Хронометраж")
        timer_layout = QHBoxLayout(timer_group)
        timer_layout.setContentsMargins(15, 15, 15, 15)
        timer_layout.setSpacing(20)

        # Крупный таймер
        self.timer_label = QLabel("00:00.0")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("""
            QLabel {
                font-size: 56px;
                font-family: 'Consolas', 'Monospace';
                font-weight: bold;
                color: #222;
                background: #f5f5f5;
                border: 3px solid #ddd;
                border-radius: 8px;
                padding: 10px 30px;
            }
        """)
        self.timer_label.setMinimumWidth(350)
        timer_layout.addWidget(self.timer_label, 1)

        # Кнопки управления таймером
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_start = QPushButton("START\n(Space)")
        self.btn_start.setMinimumSize(100, 60)
        self.btn_start.setStyleSheet("""
            QPushButton {
                font-size: 16px; font-weight: bold;
                background: #2ecc71; color: white;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #27ae60; }
            QPushButton:pressed { background: #1e8a49; }
            QPushButton:disabled { background: #95d6a4; }
        """)
        self.btn_start.clicked.connect(self._on_start)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setMinimumSize(100, 60)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                font-size: 16px; font-weight: bold;
                background: #e74c3c; color: white;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #c0392b; }
            QPushButton:pressed { background: #a93226; }
            QPushButton:disabled { background: #f5a9a9; }
        """)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setEnabled(False)

        self.btn_reset = QPushButton("RESET")
        self.btn_reset.setMinimumSize(100, 60)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                font-size: 16px; font-weight: bold;
                background: #f39c12; color: white;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #e67e22; }
            QPushButton:pressed { background: #d35400; }
            QPushButton:disabled { background: #f7c97e; }
        """)
        self.btn_reset.clicked.connect(self._on_reset)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()

        timer_layout.addLayout(btn_layout)
        main_layout.addWidget(timer_group)

        # === СРЕДНЯЯ ЧАСТЬ: ВВОД ДАННЫХ ===
        input_group = QGroupBox("Финиш участника")
        input_layout = QGridLayout(input_group)
        input_layout.setContentsMargins(15, 15, 15, 15)
        input_layout.setHorizontalSpacing(15)
        input_layout.setVerticalSpacing(10)

        # Номер
        input_layout.addWidget(QLabel("Номер:"), 0, 0)
        self.number_edit = NumberLineEdit()
        self.number_edit.setFixedWidth(150)
        self.number_edit.finish_requested.connect(self._on_finish)
        input_layout.addWidget(self.number_edit, 0, 1)

        # Ручное время
        input_layout.addWidget(QLabel("Ручное время:"), 0, 2)
        self.manual_time_edit = ManualTimeLineEdit()
        self.manual_time_edit.setFixedWidth(220)
        self.manual_time_edit.finish_requested.connect(self._on_finish)
        input_layout.addWidget(self.manual_time_edit, 0, 3)

        # Кнопка Finish!
        self.btn_finish = QPushButton("Finish!\n(Enter)")
        self.btn_finish.setMinimumSize(120, 50)
        self.btn_finish.setStyleSheet("""
            QPushButton {
                font-size: 18px; font-weight: bold;
                background: #3498db; color: white;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background: #2980b9; }
            QPushButton:pressed { background: #1f618d; }
            QPushButton:disabled { background: #85c1e9; }
        """)
        self.btn_finish.clicked.connect(self._on_finish)
        self.btn_finish.setEnabled(False)
        input_layout.addWidget(self.btn_finish, 0, 4, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Статус загруженного файла
        self.reg_file_label = QLabel("Файл регистрации: не загружен")
        self.reg_file_label.setStyleSheet("color: #666; font-size: 12px;")
        input_layout.addWidget(self.reg_file_label, 1, 0, 1, 5)

        main_layout.addWidget(input_group)

        # === ТАБЛИЦА РЕЗУЛЬТАТОВ ===
        self.results_table = ResultsTable()
        self.results_table.cell_changed.connect(self._on_table_cell_changed)
        main_layout.addWidget(self.results_table, 1)

        # === СТАТУС БАР ===
        self.status_bar = StatusBar()
        self.status_bar.error_logged.connect(self.logger.log)
        self.setStatusBar(self.status_bar)

        # Начальное состояние кнопок
        self._update_finish_button()

    def _setup_shortcuts(self) -> None:
        # Space - START/STOP
        shortcut_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        shortcut_space.activated.connect(self._on_space)

        # Escape - RESET
        shortcut_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        shortcut_esc.activated.connect(self._on_reset)

        # Ctrl+O - Открыть файл регистрации
        shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut_open.activated.connect(self._on_load_registration)

        # Ctrl+S - Сохранить отчёт
        shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_save.activated.connect(self._on_export_report)

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        # Файл
        file_menu = menubar.addMenu("Файл")

        act_load = QAction("Загрузить регистрацию (Ctrl+O)", self)
        act_load.triggered.connect(self._on_load_registration)
        file_menu.addAction(act_load)

        act_export = QAction("Экспорт отчёта (Ctrl+S)", self)
        act_export.triggered.connect(self._on_export_report)
        file_menu.addAction(act_export)

        file_menu.addSeparator()

        act_exit = QAction("Выход", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Таймер
        timer_menu = menubar.addMenu("Таймер")

        act_start = QAction("Старт (Space)", self)
        act_start.triggered.connect(self._on_start)
        timer_menu.addAction(act_start)

        act_stop = QAction("Стоп (Space)", self)
        act_stop.triggered.connect(self._on_stop)
        timer_menu.addAction(act_stop)

        act_reset = QAction("Сброс (Esc)", self)
        act_reset.triggered.connect(self._on_reset)
        timer_menu.addAction(act_reset)

        # Справка
        help_menu = menubar.addMenu("Справка")

        act_about = QAction("О программе", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # === ОБРАБОТЧИКИ СОБЫТИЙ ===

    def _on_timer_tick(self, elapsed: timedelta) -> None:
        self.timer_label.setText(format_time_short(elapsed))

    def _update_timer_buttons(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.btn_reset.setEnabled(True)

    def _update_finish_button(self) -> None:
        has_reg = len(self.participants) > 0
        has_number = self.number_edit.get_number() is not None
        self.btn_finish.setEnabled(has_reg and has_number)

    @Slot()
    def _on_start(self) -> None:
        if not self.participants:
            self.status_bar.show_warning("Сначала загрузите файл регистрации")
            return
        self.timer.start()
        self.status_bar.show_info("Таймер запущен")

    @Slot()
    def _on_stop(self) -> None:
        self.timer.stop()
        self.status_bar.show_info("Таймер остановлен")

    @Slot()
    def _on_reset(self) -> None:
        self.timer.reset()
        self.status_bar.show_info("Таймер сброшен")

    @Slot()
    def _on_space(self) -> None:
        if self.timer.running:
            self._on_stop()
        else:
            self._on_start()

    @Slot()
    def _on_finish(self) -> None:
        number = self.number_edit.get_number()
        if number is None:
            self.status_bar.show_error("Введите номер участника")
            return

        participant = get_participant_by_number(self.participants, number)
        if participant is None:
            self.status_bar.show_error(f"Участник с номером {number} не найден")
            return

        # Ручное время (опционально)
        manual_time = self.manual_time_edit.get_time()

        # Создаём запись
        record = FinishRecord(
            participant=participant,
            timer_time=self.timer.elapsed,
            manual_time=manual_time,
        )

        # Вычисляем итоговое время
        record.final_time = calculate_all_results([record], self.common_start)[0].final_time

        # Добавляем в список
        self.finishes.append(record)

        # Пересчитываем все места
        sorted_finishes = calculate_all_results(self.finishes, self.common_start)
        self.finishes = sorted_finishes

        # Обновляем таблицу
        self._refresh_table()

        # Очищаем ввод
        self.number_edit.clear_input()
        self.manual_time_edit.clear_input()
        self._update_finish_button()

        # Автосохранение
        self._autosave()

        self.status_bar.show_info(f"Финиш записан: #{number} {participant.full_name}")

    def _on_table_cell_changed(self, row: int, col: int, new_value: str) -> None:
        """Обработка ручного редактирования таблицы."""
        if row >= len(self.finishes):
            return

        record = self.finishes[row]

        try:
            if col == 1:  # Номер
                new_num = int(new_value)
                participant = get_participant_by_number(self.participants, new_num)
                if participant:
                    record.participant = participant
                    record.is_edited = True
                else:
                    self.status_bar.show_error(f"Участник #{new_num} не найден")
                    self._refresh_table()  # откат
                    return

            elif col == 4:  # Ручное время
                if new_value.strip():
                    td = validate_manual_time(new_value)
                    if td is not None:
                        record.manual_time = td
                        record.is_edited = True
                    else:
                        self.status_bar.show_error("Неверный формат времени")
                        self._refresh_table()
                        return
                else:
                    record.manual_time = None
                    record.is_edited = True

            elif col == 5:  # Штраф секунды
                record.penalty_seconds = float(new_value) if new_value else 0.0
                record.is_edited = True

            elif col == 6:  # Штраф баллы
                record.penalty_points = int(new_value) if new_value else 0
                record.is_edited = True

            # Пересчёт
            sorted_finishes = calculate_all_results(self.finishes, self.common_start)
            self.finishes = sorted_finishes
            self._refresh_table()

        except ValueError as e:
            self.status_bar.show_error(f"Ошибка значения: {e}")
            self._refresh_table()

    def _on_load_registration(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть файл регистрации", "",
            "Excel файлы (*.xlsx *.xls);;Все файлы (*.*)"
        )
        if not file_path:
            return

        try:
            participants, common_start = self.excel_importer.load(file_path)

            self.participants = participants
            self.common_start = common_start
            self.registration_file = file_path

            self.reg_file_label.setText(f"Файл регистрации: {Path(file_path).name} ({len(participants)} участников)")
            if common_start:
                self.reg_file_label.setText(
                    self.reg_file_label.text() + f" | Общий старт: +{format_time_short(common_start)}"
                )

            # Включаем кнопку Finish
            self._update_finish_button()

            self.status_bar.set_permanent(f"Загружено участников: {len(participants)}")
            self.status_bar.show_info("Файл регистрации загружен")

            # Сохраняем состояние
            self._autosave()

        except Exception as e:
            self.logger.log("ERROR", f"Ошибка загрузки регистрации: {e}")
            self.status_bar.show_error(f"Ошибка загрузки: {e}")

    def _on_export_report(self) -> None:
        if not self.finishes:
            self.status_bar.show_warning("Нет данных для экспорта")
            return

        dir_path = QFileDialog.getExistingDirectory(self, "Выберите папку для отчёта")
        if not dir_path:
            return

        try:
            # Пересчитываем перед экспортом
            sorted_finishes = calculate_all_results(self.finishes, self.common_start)

            excel_path = self.exporter.export_excel(sorted_finishes, dir_path, self.registration_file)
            csv_path = self.exporter.export_csv(sorted_finishes, dir_path)

            self.status_bar.show_info(f"Отчёт сохранён: {Path(excel_path).name}, {Path(csv_path).name}")

        except Exception as e:
            self.logger.log("ERROR", f"Ошибка экспорта: {e}")
            self.status_bar.show_error(f"Ошибка экспорта: {e}")

    def _refresh_table(self) -> None:
        self.results_table.blockSignals(True)
        try:
            self.results_table.setRowCount(0)
            for record in self.finishes:
                self.results_table.add_result(record, record.place)
        finally:
            self.results_table.blockSignals(False)

    def _autosave(self) -> None:
        state = CompetitionState(
            registration_file=self.registration_file,
            participants=self.participants,
            finishes=self.finishes,
            timer_elapsed=self.timer.elapsed,
            timer_running=self.timer.running,
            common_start_offset=self.common_start,
            pending_number=self.number_edit.text(),
            pending_manual_time=self.manual_time_edit.text(),
        )
        self.state_manager.save(state)

    def _restore_state(self) -> None:
        state = self.state_manager.load()
        if state is None:
            return

        # Восстанавливаем участников
        if state.participants:
            self.participants = state.participants
            self.reg_file_label.setText(f"Файл регистрации: {Path(state.registration_file).name} ({len(self.participants)} участников)")
            if state.common_start_offset:
                self.reg_file_label.setText(
                    self.reg_file_label.text() + f" | Общий старт: +{format_time_short(state.common_start_offset)}"
                )
            self._update_finish_button()

        # Восстанавливаем финиши
        self.finishes = state.finishes
        self._refresh_table()

        # Восстанавливаем таймер
        self.common_start = state.common_start_offset
        self.timer.restore_state(TimerState(state.timer_elapsed, state.timer_running))

        # Восстанавливаем ввод
        self.number_edit.setText(state.pending_number)
        self.manual_time_edit.setText(state.pending_manual_time)

        self.status_bar.set_permanent("Состояние восстановлено")

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "О программе",
            f"<b>{get_app_title()}</b><br>"
            "Судейский хронометраж и учет результатов<br><br>"
            f"Версия: {get_version()}<br>"
            "Python + PySide6 + openpyxl<br>"
            "© 2024 ChronoJudge Team"
        )

    def closeEvent(self, event) -> None:
        """Сохранение состояния при закрытии."""
        self._autosave()
        self.logger.close()
        event.accept()


def main() -> int:
    """Точка входа приложения."""
    app = QApplication(sys.argv)
    app.setApplicationName("ChronoJudge")
    app.setApplicationVersion(get_version())

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
