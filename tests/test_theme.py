"""Tests for the design-system theme registry, stylesheet, and glyphs."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from udm.constants import DEFAULT_CONFIG
from udm.ui.theme import (
    DEFAULT_THEME,
    SYSTEM_OPTION,
    THEME_OPTIONS,
    build_stylesheet,
    render_glyph,
    resolve_theme,
    stylesheet_for,
    theme_for,
)
from udm.ui.theme.glyphs import ACTION_GLYPHS, TAB_GLYPHS

_CONCRETE_THEMES = ["Refined Dark", "Light"]
_EXTRA_GLYPHS = ["check", "queue", "sync"]


class ThemeRegistryTests(unittest.TestCase):
    def test_expected_options_and_system_default(self):
        self.assertEqual(THEME_OPTIONS, ["System", "Refined Dark", "Light"])
        self.assertEqual(DEFAULT_THEME, SYSTEM_OPTION)
        self.assertIn(DEFAULT_THEME, THEME_OPTIONS)

    def test_default_config_theme_is_a_known_option(self):
        self.assertIn(DEFAULT_CONFIG["theme"], THEME_OPTIONS)

    def test_system_resolves_by_os_preference(self):
        self.assertEqual(resolve_theme(SYSTEM_OPTION, True).name, "Refined Dark")
        self.assertEqual(resolve_theme(SYSTEM_OPTION, False).name, "Light")

    def test_concrete_option_ignores_os_preference(self):
        self.assertEqual(resolve_theme("Light", True).name, "Light")
        self.assertEqual(resolve_theme("Refined Dark", False).name, "Refined Dark")

    def test_unknown_theme_falls_back_to_default_concrete(self):
        self.assertEqual(theme_for("Does Not Exist").name, "Refined Dark")


class StylesheetTests(unittest.TestCase):
    def test_every_theme_builds_a_scrollbar_styled_sheet(self):
        for name in _CONCRETE_THEMES:
            sheet = stylesheet_for(name)
            self.assertIsInstance(sheet, str)
            self.assertTrue(sheet.strip())
            self.assertIn("QScrollBar", sheet)

    def test_unknown_theme_still_builds_default_sheet(self):
        self.assertEqual(stylesheet_for("Nope"), stylesheet_for("Refined Dark"))


class GlyphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_every_mapped_glyph_renders_a_non_null_icon(self):
        names = list({**ACTION_GLYPHS, **TAB_GLYPHS}.values()) + _EXTRA_GLYPHS
        for key in names:
            icon = render_glyph(key, "#e6e8eb")
            self.assertFalse(icon.pixmap(20, 20).isNull(), key)

    def test_unknown_glyph_returns_empty_icon(self):
        self.assertTrue(render_glyph("missing", "#ffffff").isNull())


class CheckmarkAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_checkmark_renders_to_a_file(self):
        from udm.ui.theme.assets import glyph_asset_url

        url = glyph_asset_url("check", "#ffffff")
        self.assertTrue(url)
        self.assertTrue(os.path.exists(url))

    def test_stylesheet_embeds_checkmark_image_when_provided(self):
        sheet = build_stylesheet(theme_for("Refined Dark"), checkmark_url="/x.png")
        self.assertIn("image: url(/x.png)", sheet)


class DevReloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_disabled_without_env_returns_no_watcher(self):
        from udm.ui.dev_reload import install_style_hot_reload

        os.environ.pop("UDM_DEV", None)
        self.assertIsNone(install_style_hot_reload(object()))

    def test_enabled_returns_a_watcher(self):
        from PyQt6.QtCore import QFileSystemWatcher

        from udm.ui.dev_reload import install_style_hot_reload

        os.environ["UDM_DEV"] = "1"
        try:
            watcher = install_style_hot_reload(object())
            self.assertIsInstance(watcher, QFileSystemWatcher)
        finally:
            os.environ.pop("UDM_DEV", None)


if __name__ == "__main__":
    unittest.main()
