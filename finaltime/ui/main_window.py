"""Главное окно приложения."""

import base64
import sys
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import ctypes

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QBitmap, QIcon, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDateEdit,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from finaltime import get_app_title, get_version
from finaltime.core import (
    AgeCategory,
    AppTimer,
    CompetitionState,
    FinishRecord,
    Gender,
    Participant,
    TimerState,
    calculate_all_results,
    format_time_short,
    get_participant_by_number,
    parse_time_str,
    validate_manual_time,
)
from finaltime.io import ExcelImporter, Exporter, StateManager, CategoriesImporter
from finaltime.services import Logger, SessionManager
from finaltime.assets.icon_data import ICON_ICO_B64
from finaltime.ui.status_bar import StatusBar
from finaltime.ui.widgets import HoldButton, ManualTimeLineEdit, NumberLineEdit, ResultsTable


class MainWindow(QMainWindow):
    """Главное окно приложения FinalTime."""

    def __init__(self):
        super().__init__()

        # Версия в заголовке
        self.setWindowTitle(get_app_title())
        self.resize(1200, 800)
        self.setMinimumSize(1000, 650)

        # Иконка окна
        self.setWindowIcon(_load_icon())

        # Сервисы
        self.logger = Logger()
        self.session = SessionManager(self.logger)
        self.state_manager = StateManager(self.logger)
        self.excel_importer = ExcelImporter(self.logger)
        self.categories_importer = CategoriesImporter(self.logger)
        self.exporter = Exporter(self.logger)

        # Данные
        self.competition_name: str = ""
        self.participants: list[Participant] = []
        self.finishes: list[FinishRecord] = []
        self.common_start: timedelta | None = None
        self.registration_file: str = ""
        self.categories_file: str = ""
        self.categories: list[AgeCategory] = []
        self.competition_date: date = date.today()

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

        # Счётчик порядка финишей
        self._finish_sequence = 0

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 10)

        # === ВЕРХНЯЯ ЧАСТЬ: ПАРАМЕТРЫ СОРЕВНОВАНИЙ ===
        top_group = QGroupBox("Параметры соревнований")
        top_layout = QVBoxLayout(top_group)
        top_layout.setContentsMargins(15, 15, 15, 15)
        top_layout.setSpacing(10)

        # Ряд 1: Название соревнований + Дата
        row1 = QHBoxLayout()
        row1.setSpacing(15)

        row1.addWidget(QLabel("Название соревнований:"))
        self.competition_name_edit = QLineEdit()
        self.competition_name_edit.setPlaceholderText("например, Чемпионат города по лёгкой атлетике")
        self.competition_name_edit.setMinimumWidth(250)
        self.competition_name_edit.textChanged.connect(self._on_competition_name_changed)
        row1.addWidget(self.competition_name_edit, 1)

        row1.addSpacing(20)

        row1.addWidget(QLabel("Дата соревнований:"))
        self.competition_date_edit = QDateEdit()
        self.competition_date_edit.setCalendarPopup(True)
        self.competition_date_edit.setDate(self.competition_date)
        self.competition_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.competition_date_edit.setFixedWidth(130)
        self.competition_date_edit.dateChanged.connect(self._on_competition_date_changed)
        row1.addWidget(self.competition_date_edit)

        top_layout.addLayout(row1)

        # Ряд 2: Регистрация + Категории с кнопками
        row2 = QHBoxLayout()
        row2.setSpacing(15)

        # Регистрация
        row2.addWidget(QLabel("Регистрация:"))
        self.registration_file_label = QLabel("не загружен")
        self.registration_file_label.setStyleSheet("color: #666; font-size: 12px;")
        self.registration_file_label.setMinimumWidth(180)
        row2.addWidget(self.registration_file_label, 1)

        self.btn_load_registration = QPushButton("Загрузить регистрацию")
        self.btn_load_registration.setFixedWidth(170)
        self.btn_load_registration.clicked.connect(self._on_load_registration)
        row2.addWidget(self.btn_load_registration)

        row2.addSpacing(20)

        # Категории
        row2.addWidget(QLabel("Категории:"))
        self.categories_file_label = QLabel("не загружен")
        self.categories_file_label.setStyleSheet("color: #666; font-size: 12px;")
        self.categories_file_label.setMinimumWidth(180)
        row2.addWidget(self.categories_file_label, 1)

        self.btn_load_categories = QPushButton("Загрузить категории")
        self.btn_load_categories.setFixedWidth(170)
        self.btn_load_categories.clicked.connect(self._on_load_categories)
        row2.addWidget(self.btn_load_categories)

        top_layout.addLayout(row2)

        main_layout.addWidget(top_group)

        # === ТАЙМЕР ===
        timer_group = QGroupBox("Хронометраж")
        timer_layout = QHBoxLayout(timer_group)
        timer_layout.setContentsMargins(15, 15, 15, 15)
        timer_layout.setSpacing(20)

        # Крупный таймер с подписями HHH / MM / SS.S
        timer_display = QWidget()
        timer_display.setStyleSheet(
            "background: #f5f5f5; border-radius: 8px;"
        )
        timer_display_layout = QVBoxLayout(timer_display)
        timer_display_layout.setContentsMargins(20, 8, 20, 10)
        timer_display_layout.setSpacing(0)

        # Подписи над значениями (без рамок, двоеточия невидимы для выравнивания)
        labels_row = QHBoxLayout()
        labels_row.setSpacing(2)
        unit_style = "font-size: 15px; font-weight: bold; color: #999; font-family: 'Consolas', 'Monospace'; background: transparent;"
        labels_row.addStretch(1)
        for i, text in enumerate(("HHH", "MM", "SS.S")):
            if i > 0:
                colon_spacer = QLabel(":")
                colon_spacer.setStyleSheet("font-size: 15px; font-weight: bold; color: transparent; font-family: 'Consolas', 'Monospace';")
                labels_row.addWidget(colon_spacer)
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(unit_style)
            labels_row.addWidget(lbl)
        labels_row.addStretch(1)
        timer_display_layout.addLayout(labels_row)

        # Значения HHH:MM:SS.S — плотно по центру, с двоеточиями
        values_row = QHBoxLayout()
        values_row.setSpacing(2)
        value_style = "font-size: 96px; font-family: 'Consolas', 'Monospace'; font-weight: bold; color: #222; background: transparent;"
        self.timer_h_label = QLabel("000")
        self.timer_h_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_h_label.setStyleSheet(value_style)
        self.timer_m_label = QLabel("00")
        self.timer_m_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_m_label.setStyleSheet(value_style)
        self.timer_s_label = QLabel("00.0")
        self.timer_s_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_s_label.setStyleSheet(value_style)
        values_row.addStretch(1)
        values_row.addWidget(self.timer_h_label)
        colon1 = QLabel(":")
        colon1.setStyleSheet(value_style)
        values_row.addWidget(colon1)
        values_row.addWidget(self.timer_m_label)
        colon2 = QLabel(":")
        colon2.setStyleSheet(value_style)
        values_row.addWidget(colon2)
        values_row.addWidget(self.timer_s_label)
        values_row.addStretch(1)
        timer_display_layout.addLayout(values_row)

        self.timer_label = timer_display  # для совместимости (используется как контейнер)
        timer_display.setMinimumWidth(300)
        timer_layout.addWidget(timer_display, 1)

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

        self.btn_stop = HoldButton("STOP")
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
        self.btn_stop.hold_activated.connect(self._on_stop)
        self.btn_stop.setEnabled(False)

        self.btn_reset = HoldButton("RESET")
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
        self.btn_reset.hold_activated.connect(self._on_reset)

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
        self.number_edit.textChanged.connect(self._update_finish_button)
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

        # Статус загруженных файлов
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
        # Space - START
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

        act_load_cat = QAction("Загрузить категории...", self)
        act_load_cat.triggered.connect(self._on_load_categories)
        file_menu.addAction(act_load_cat)

        file_menu.addSeparator()

        act_export = QAction("Экспорт отчёта (Ctrl+S)", self)
        act_export.triggered.connect(self._on_export_report)
        file_menu.addAction(act_export)

        file_menu.addSeparator()

        act_clean = QAction("Чистая загрузка", self)
        act_clean.triggered.connect(self._on_clean_load)
        file_menu.addAction(act_clean)

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
        total = elapsed.total_seconds()
        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)
        seconds = total % 60
        self.timer_h_label.setText(f"{hours:03d}")
        self.timer_m_label.setText(f"{minutes:02d}")
        self.timer_s_label.setText(f"{seconds:04.1f}")

    def _update_timer_buttons(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.btn_reset.setEnabled(True)

    def _update_finish_button(self) -> None:
        has_reg = len(self.participants) > 0
        has_number = self.number_edit.get_number() is not None
        self.btn_finish.setEnabled(has_reg and has_number)

    @Slot()
    def _on_competition_date_changed(self, qdate) -> None:
        """Изменение даты соревнований."""
        self.competition_date = qdate.toPython()
        self._refresh_table()  # Пересчитываем категории в таблице
        self._autosave()
        self.status_bar.show_info(f"Дата соревнований: {self.competition_date.strftime('%d.%m.%Y')}")

    def _on_competition_name_changed(self, text: str) -> None:
        """Изменение названия соревнований."""
        self.competition_name = text.strip()
        self._autosave()

    @Slot()
    def _on_load_categories(self) -> None:
        """Загрузка файла категорий."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть файл категорий", "",
            "Excel файлы (*.xlsx *.xls);;Все файлы (*.*)"
        )
        if not file_path:
            return

        try:
            categories = self.categories_importer.load(file_path)
            self.categories = categories
            self.categories_file = file_path

            self.categories_file_label.setText(f"{Path(file_path).name} ({len(categories)} кат.)")
            self.categories_file_label.setStyleSheet("color: #27ae60; font-size: 12px;")

            self.status_bar.set_permanent(f"Категорий: {len(categories)}")
            self.status_bar.show_info("Файл категорий загружен")

            # Обновляем таблицу с новыми категориями
            self._refresh_table()
            self._autosave()

        except Exception as e:
            self.logger.log("ERROR", f"Ошибка загрузки категорий: {e}")
            self.status_bar.show_error(f"Ошибка загрузки категорий: {e}")

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

    def _on_clean_load(self) -> None:
        """Полный сброс состояния приложения к начальному."""
        answer = QMessageBox.question(
            self, "Чистая загрузка",
            "Сбросить всё состояние программы?\n\n"
            "Будут удалены:\n"
            "- участники и результаты\n"
            "- категории\n"
            "- состояние таймера и ввода\n"
            "- сохранённое состояние (state.json)\n\n"
            "Это действие необратимо.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        # Сброс данных
        self.competition_name = ""
        self.participants = []
        self.finishes = []
        self.categories = []
        self.common_start = None
        self.registration_file = ""
        self.categories_file = ""
        self.competition_date = date.today()

        # Сброс таймера
        self.timer.reset()

        # Сброс ввода
        self.number_edit.clear_input()
        self.manual_time_edit.clear_input()
        self._update_finish_button()

        # Сброс UI
        self.competition_name_edit.setText("")
        self.competition_date_edit.setDate(self.competition_date)
        self.reg_file_label.setText("Файл регистрации: не загружен")
        self.reg_file_label.setStyleSheet("color: #666; font-size: 12px;")
        self.registration_file_label.setText("не загружен")
        self.registration_file_label.setStyleSheet("color: #666; font-size: 12px;")
        self.categories_file_label.setText("не загружен")
        self.categories_file_label.setStyleSheet("color: #666; font-size: 12px;")
        self.results_table.setRowCount(0)

        # Удаление сохранённого состояния
        self.state_manager.clear()

        self.status_bar.set_permanent("Чистая загрузка: состояние сброшено")

    @Slot()
    def _on_space(self) -> None:
        # Пробел — только СТАРТ. Стоп — только кнопкой мыши.
        if not self.timer.running:
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

        # Создаём запись с порядковым номером
        self._finish_sequence += 1
        record = FinishRecord(
            participant=participant,
            timer_time=self.timer.elapsed,
            manual_time=manual_time,
            sequence=self._finish_sequence,
        )

        # Вычисляем итоговое время
        record.final_time = calculate_all_results([record], self.common_start)[0].final_time

        # Добавляем в список (хронологический порядок)
        self.finishes.append(record)

        # Обновляем таблицу (показываем свежие сверху)
        self._refresh_table()

        # Очищаем ввод, фокус возвращаем в поле номера участника
        self.number_edit.clear()
        self.manual_time_edit.clear()
        self.number_edit.setFocus()
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

            # Обновляем таблицу (места пересчитаются в _refresh_table)
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

            # Верхняя панель: название файла регистрации
            self.registration_file_label.setText(Path(file_path).name)
            self.registration_file_label.setStyleSheet("color: #27ae60; font-size: 12px;")

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

            excel_path = self.exporter.export_excel(
                sorted_finishes, dir_path, self.registration_file,
                self.competition_date, self.categories, self.competition_name
            )
            csv_path = self.exporter.export_csv(
                sorted_finishes, dir_path,
                self.competition_date, self.categories, self.competition_name
            )

            self.status_bar.show_info(f"Отчёт сохранён: {Path(excel_path).name}, {Path(csv_path).name}")

        except Exception as e:
            self.logger.log("ERROR", f"Ошибка экспорта: {e}")
            self.status_bar.show_error(f"Ошибка экспорта: {e}")

    def _refresh_table(self) -> None:
        self.results_table.blockSignals(True)
        try:
            self.results_table.setRowCount(0)
            # Считаем места по времени (для отображения в колонке Место)
            sorted_by_time = calculate_all_results(self.finishes, self.common_start)
            place_by_id = {id(r): r.place for r in sorted_by_time}
            # Показываем в обратном хронологическом порядке (свежие сверху)
            for record in reversed(self.finishes):
                display_place = place_by_id.get(id(record), 0)
                self.results_table.add_result(
                    record, display_place,
                    self.competition_date, self.categories
                )
        finally:
            self.results_table.blockSignals(False)

    def _autosave(self) -> None:
        ts = self.timer.get_state()
        state = CompetitionState(
            competition_name=self.competition_name,
            registration_file=self.registration_file,
            categories_file=self.categories_file,
            competition_date=self.competition_date.isoformat(),
            participants=self.participants,
            finishes=self.finishes,
            timer_elapsed=ts.elapsed,
            timer_running=ts.running,
            timer_base_elapsed=format_time_short(ts.base_elapsed),
            timer_started_at=ts.started_at,
            common_start_offset=self.common_start,
            pending_number=self.number_edit.text(),
            pending_manual_time=self.manual_time_edit.text(),
        )
        self.state_manager.save(state)

    def _restore_state(self) -> None:
        state = self.state_manager.load()
        if state is None:
            return

        # Восстанавливаем название соревнований
        self.competition_name = state.competition_name
        self.competition_name_edit.setText(state.competition_name)

        # Восстанавливаем дату соревнования
        if state.competition_date:
            try:
                self.competition_date = date.fromisoformat(state.competition_date)
                self.competition_date_edit.setDate(self.competition_date)
            except ValueError:
                pass

        # Восстанавливаем участников
        if state.participants:
            self.participants = state.participants
            # Восстанавливаем путь к файлу регистрации
            self.registration_file = state.registration_file
            self.reg_file_label.setText(f"Файл регистрации: {Path(state.registration_file).name} ({len(self.participants)} участников)")
            if state.common_start_offset:
                self.reg_file_label.setText(
                    self.reg_file_label.text() + f" | Общий старт: +{format_time_short(state.common_start_offset)}"
                )
            # Верхняя панель: название файла регистрации
            self.registration_file_label.setText(Path(state.registration_file).name)
            self.registration_file_label.setStyleSheet("color: #27ae60; font-size: 12px;")
            self._update_finish_button()

        # Восстанавливаем категории
        if state.categories_file and Path(state.categories_file).exists():
            try:
                categories = self.categories_importer.load(state.categories_file)
                self.categories = categories
                self.categories_file = state.categories_file
                self.categories_file_label.setText(f"{Path(state.categories_file).name} ({len(categories)} кат.)")
                self.categories_file_label.setStyleSheet("color: #27ae60; font-size: 12px;")
            except Exception as e:
                self.logger.log("WARNING", f"Failed to restore categories: {e}")

        # Восстанавливаем финиши
        self.finishes = state.finishes
        self._refresh_table()

        # Восстанавливаем таймер (реальное время от системных часов)
        self.common_start = state.common_start_offset
        timer_state = TimerState(
            elapsed=state.timer_elapsed,
            running=state.timer_running,
            base_elapsed=parse_time_str(state.timer_base_elapsed) if state.timer_base_elapsed else timedelta(0),
            started_at=state.timer_started_at,
        )
        self.timer.restore_state(timer_state)
        # Обновляем кнопки таймера вручную
        self._update_timer_buttons(self.timer.running)

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
            "© 2024 FinalTime Team"
        )

    def closeEvent(self, event) -> None:
        """Сохранение состояния при закрытии."""
        self._autosave()
        self.logger.close()
        event.accept()


def _load_icon() -> QIcon:
    """Загружает иконку из base64 данных."""
    icon_data = base64.b64decode(ICON_ICO_B64)
    pixmap = QPixmap()
    pixmap.loadFromData(icon_data)
    return QIcon(pixmap)


def main() -> int:
    """Точка входа приложения."""
    # Windows: иконка в панели задач
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "FinalTime.App"
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("FinalTime")
    app.setApplicationVersion(get_version())

    # Установка иконки приложения (панель задач + заголовок окна)
    app_icon = _load_icon()
    app.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())