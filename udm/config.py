"""Configuration persistence and download category routing."""

from copy import deepcopy
import json
import logging
from pathlib import Path

from udm.constants import DEFAULT_CONFIG


class ConfigManager:
    """Load, merge, save, and query application configuration."""

    def __init__(self, config_path="udm_config.json", download_root=None):
        self.config_path = Path(config_path)
        self.download_root = Path(download_root or Path.home() / "Downloads" / "UDM")
        self.config = self.load_config()

    def load_config(self):
        """Load saved settings and merge them with current defaults."""
        if not self.config_path.exists():
            config = deepcopy(DEFAULT_CONFIG)
            self.save_config(config)
            return config

        try:
            with self.config_path.open(encoding="utf-8") as config_file:
                saved = json.load(config_file)
        except (OSError, ValueError, TypeError) as error:
            logging.error("Config load error: %s", error)
            return deepcopy(DEFAULT_CONFIG)

        return self._merge_defaults(saved)

    def _merge_defaults(self, saved):
        # Start from a deep copy so one manager cannot mutate global defaults or
        # leak nested schedule/category changes into another manager instance.
        merged = deepcopy(DEFAULT_CONFIG)
        if not isinstance(saved, dict):
            return merged

        for key, value in saved.items():
            if key == "categories" and isinstance(value, dict):
                merged[key] = value
            elif key == "schedules" and isinstance(value, list):
                merged[key] = value
            else:
                merged[key] = value
        return merged

    def save_config(self, config_data):
        """Persist a defensive copy of the complete configuration."""
        self.config = deepcopy(config_data)
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with self.config_path.open("w", encoding="utf-8") as config_file:
                json.dump(self.config, config_file, indent=4, ensure_ascii=False)
        except OSError as error:
            logging.error("Config save error: %s", error)

    def get_category_path(self, filename):
        """Return and create the configured download directory for a filename."""
        extension = Path(filename).suffix.lower().lstrip(".")
        categories = self.config.get("categories", {})

        for category, extension_text in categories.items():
            extensions = {
                item.strip().lower().lstrip(".")
                for item in extension_text.split(",")
                if item.strip()
            }
            if extension in extensions:
                return self._ensure_category(category)

        return self._ensure_category("Others")

    def _ensure_category(self, category):
        path = self.download_root / category
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
