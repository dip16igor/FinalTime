"""Импорт файла регистрации из Excel."""

import openpyxl
from datetime import timedelta
from pathlib import Path
from typing import Optional, Tuple, List

from chronojudge.core import Participant, parse_time_offset


class ExcelImporter:
    """Загрузка участников из Excel-файла регистрации."""
    
    def __init__(self, logger):
        self.logger = logger
        
        # Настраиваемые индексы столбцов (0-based)
        # Можно вынести в конфиг позже
        self.col_number = 0      # Номер участника
        self.col_name = 1        # ФИО
        self.col_start = 2       # Стартовое время (опционально)
    
    def load(self, file_path: str) -> Tuple[List[Participant], Optional[timedelta]]:
        """Загружает участников из Excel.
        
        Returns:
            (список участников, общий старт или None)
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active
        
        participants = []
        common_start = None
        has_personal_starts = False
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(c is None for c in row):
                continue
            
            try:
                # Номер
                raw_number = row[self.col_number] if len(row) > self.col_number else None
                if raw_number is None:
                    continue
                number = int(raw_number)
                
                # ФИО
                raw_name = row[self.col_name] if len(row) > self.col_name else None
                name = str(raw_name).strip() if raw_name else f"Участник {number}"
                
                # Старт
                start_offset = None
                if len(row) > self.col_start:
                    raw_start = row[self.col_start]
                    if raw_start is not None:
                        start_str = str(raw_start).strip()
                        if start_str and start_str.lower() not in ("", "none", "null", "-"):
                            start_offset = parse_time_offset(start_str)
                            if start_offset:
                                has_personal_starts = True
                
                participant = Participant(
                    number=number,
                    full_name=name,
                    start_offset=start_offset
                )
                participants.append(participant)
                
            except (ValueError, IndexError) as e:
                self.logger.log("WARNING", f"Строка {row_idx}: ошибка парсинга - {e}")
                continue
        
        if not participants:
            raise ValueError("Не найдено ни одного участника в файле")
        
        # Если есть персональные старты, общий старт не используется
        # (но можно оставить как фоллбек)
        if not has_personal_starts:
            # Можно добавить логику чтения общего старта из отдельной ячейки
            pass
        
        self.logger.log("INFO", f"Загружено участников: {len(participants)}, персональных стартов: {sum(1 for p in participants if p.has_personal_start)}")
        
        return participants, common_start
    
    def set_column_mapping(self, number: int, name: int, start: int = -1) -> None:
        """Настройка маппинга столбцов (0-based)."""
        self.col_number = number
        self.col_name = name
        self.col_start = start