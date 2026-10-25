"""Compatibility entry point for Umbrella Download Manager."""

from udm.app import main
from udm.ui.main_window import MainWindow, UDMManager

__all__ = ["MainWindow", "UDMManager", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
