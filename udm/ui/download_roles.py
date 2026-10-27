"""Qt data roles stored on download queue name items."""

from PyQt6.QtCore import Qt

SCHEDULE_ROLE = Qt.ItemDataRole.UserRole + 1
URL_ROLE = Qt.ItemDataRole.UserRole + 2
PATH_ROLE = Qt.ItemDataRole.UserRole + 3
# Integer percent on size items; absent while the total size is unknown.
PROGRESS_ROLE = Qt.ItemDataRole.UserRole + 4
