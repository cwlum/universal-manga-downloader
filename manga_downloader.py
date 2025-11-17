"""Compatibility wrapper for the Tkinter UI application."""

from __future__ import annotations

from ui.app import MangaDownloader
from ui.logging_utils import configure_logging

__all__ = ["configure_logging", "MangaDownloader", "main"]


def main(log_level: int | str | None = None) -> None:
    """Entrypoint to launch the GUI application."""

    configure_logging(log_level)
    app = MangaDownloader()
    app.mainloop()


if __name__ == "__main__":
    main()
