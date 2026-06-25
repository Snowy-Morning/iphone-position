"""PyInstaller 启动钩子：将未捕获异常写入 crash.log。"""

import os
import sys
import traceback


def _crash_log_path() -> str:
    base = os.path.dirname(os.path.abspath(sys.executable))
    return os.path.join(base, "crash.log")


def _install_excepthook() -> None:
    def _hook(exc_type, exc, tb) -> None:
        try:
            with open(_crash_log_path(), "w", encoding="utf-8") as log_file:
                traceback.print_exception(exc_type, exc, tb, file=log_file)
        except OSError:
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook


if getattr(sys, "frozen", False):
    _install_excepthook()
