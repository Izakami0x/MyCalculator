"""Application entry point."""
from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__
from .context import create_context
from .logging_setup import setup_logging
from .paths import database_path, log_path


def _install_excepthook(log: logging.Logger) -> None:
    def hook(exc_type, exc, tb):
        log.error("Unhandled exception", exc_info=(exc_type, exc, tb))
        if QApplication.instance() is not None:
            QMessageBox.critical(
                None, "Izakami", f"Something went wrong.\n\nDetails were saved to:\n{log_path()}")

    sys.excepthook = hook


def main() -> int:
    log = setup_logging()
    log.info("Starting Izakami %s", __version__)
    app = QApplication(sys.argv)
    app.setApplicationName("Izakami Risk Calculator")
    app.setApplicationVersion(__version__)
    if sys.platform == "win32":
        app.setFont(QFont("Segoe UI", 10))
    _install_excepthook(log)

    try:
        ctx = create_context(database_path())
    except Exception:
        log.exception("Startup failed")
        QMessageBox.critical(
            None, "Izakami",
            f"Izakami could not open its database.\n\nDetails were saved to:\n{log_path()}")
        return 1

    from .ui.main_window import MainWindow

    window = MainWindow(ctx)
    if ctx.settings.get_bool("start_minimized"):
        window.showMinimized()
    else:
        window.show()
    window.apply_hotkeys()
    code = app.exec()
    ctx.shutdown()
    return code
