"""ChronoJudge - Судейский хронометраж и учет результатов."""

from . import version

__version__ = version.VERSION
__app_name__ = "ChronoJudge"
__author__ = "ChronoJudge Team"

def get_version() -> str:
    """Возвращает версию приложения."""
    return __version__

def get_app_title() -> str:
    """Возвращает заголовок окна с версией."""
    return f"{__app_name__} v{__version__}"

def get_exe_name() -> str:
    """Возвращает имя exe-файла с версией."""
    return f"{__app_name__}_v{__version__}.exe"