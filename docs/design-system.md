# UDM Design System

This document defines the visual design system for the UDM desktop application.
It is the single source of truth for colors, spacing, typography, component
appearance, and theming. Every user interface change must conform to the rules
here, and new interface work must reference the named tokens defined below rather
than raw values.

The application is built with PyQt6 and styled through Qt Style Sheets (QSS),
centralized in the `udm/ui/theme/` package. QSS behaves like a restricted dialect of
CSS. This document describes the intended system; the implementation follows the
same structure so that any widget added later inherits the system automatically.

## Goals

- Consistency: one gray means one thing, one accent means one thing, everywhere.
- Modern and legible: clear hierarchy, calm surfaces, restrained accent use.
- Themeable: dark and light looks share one token structure.
- Maintainable: components reference tokens, never hard-coded hex or pixel values.

## Theme Architecture

The system is organized as one shared **token structure** with multiple
**themes** that fill that structure with concrete values. A theme never adds or
removes token names; it only changes their values. This guarantees that every
component works under every theme without per-theme component rules.

Two concrete themes carry real token values:

- **Refined Dark**: an intentional dark theme with a small, controlled gray
  palette and a single blue accent.
- **Light**: the same structure mapped to light surfaces for daytime and
  high-brightness use.

The theme selector offers a third choice, **System** (the default), which is not
a concrete theme but a mode: it follows the operating system's light or dark
preference, resolving to Light when the OS is light and Refined Dark when the OS
is dark. When System is active the application restyles live if the OS switches
between day and night.

Implementation note: QSS has no variables. Each concrete theme is a Python
mapping of token name to value, substituted into the QSS template when applied.
Selecting a theme chooses which mapping is applied; System first resolves to a
concrete theme from the OS preference. No component rule changes per theme.

## Design Tokens

Tokens are grouped by role. Names are stable; values are theme-specific. Prefer
the semantic name (`bg.raised`) over the literal value in all component rules.

### Color: Surfaces

Three surface levels only. Do not introduce additional grays; if a surface is
needed, reuse one of these.

| Token        | Role                                   | Refined Dark | Light     |
| ------------ | -------------------------------------- | ------------ | --------- |
| `bg.base`    | Window and primary background          | `#1c1e22`    | `#f6f7f9` |
| `bg.raised`  | Toolbars, cards, elevated panels       | `#26292e`    | `#ffffff` |
| `bg.sunken`  | Tables, lists, inputs, inset regions   | `#16181b`    | `#eceef1` |

### Color: Borders

| Token           | Role                                  | Refined Dark | Light     |
| --------------- | ------------------------------------- | ------------ | --------- |
| `border.subtle` | Default separators and control edges  | `#2f333a`    | `#e1e4e8` |
| `border.strong` | Emphasized edges, focus-adjacent      | `#3d424b`    | `#c9cdd3` |

### Color: Text

| Token           | Role                          | Refined Dark | Light     |
| --------------- | ----------------------------- | ------------ | --------- |
| `text.primary`  | Default readable text         | `#e6e8eb`    | `#1c1e22` |
| `text.muted`    | Secondary and helper text     | `#9aa2ad`    | `#5c636e` |
| `text.disabled` | Disabled controls             | `#5c636e`    | `#a6acb5` |

### Color: Accent

One accent family drives actions, selection, and focus. Use it sparingly so it
retains meaning.

| Token            | Role                              | Refined Dark | Light     |
| ---------------- | --------------------------------- | ------------ | --------- |
| `accent`         | Primary actions, selection, focus | `#2f81f7`    | `#2f81f7` |
| `accent.hover`   | Hover state of accent surfaces    | `#4c94f8`    | `#4c94f8` |
| `accent.pressed` | Pressed state of accent surfaces  | `#1f6feb`    | `#1f6feb` |
| `accent.text`    | Text and glyphs on accent fills   | `#ffffff`    | `#ffffff` |

### Color: Status

Status colors are reserved for meaning (state, progress, alerts), never for
decoration. Schedule marker colors (`SCHEDULE_COLORS` in `udm/constants.py`)
are a separate user-facing palette and are not status tokens.

| Token            | Meaning              | Value     |
| ---------------- | -------------------- | --------- |
| `status.success` | Completed, healthy   | `#2ea043` |
| `status.warning` | Attention, paused    | `#d29922` |
| `status.danger`  | Error, stopped       | `#f85149` |
| `status.info`    | Neutral information  | `#2f81f7` |

### Spacing

A single 4-based scale. All padding, margins, and gaps use these steps.

| Token | Value |
| ----- | ----- |
| `xs`  | 4px   |
| `sm`  | 8px   |
| `md`  | 12px  |
| `lg`  | 16px  |
| `xl`  | 24px  |

### Radius

| Token  | Value | Use                                  |
| ------ | ----- | ------------------------------------ |
| `sm`   | 4px   | Inputs, small controls               |
| `md`   | 6px   | Buttons, cards, dialogs              |
| `lg`   | 10px  | Large panels and modal containers    |
| `pill` | 999px | Toggles and fully rounded elements   |

### Control Heights

Consistent control heights keep rows and toolbars aligned.

| Token | Value | Use                          |
| ----- | ----- | ---------------------------- |
| `sm`  | 24px  | Compact inline controls      |
| `md`  | 30px  | Default buttons and inputs   |
| `lg`  | 36px  | Prominent or primary actions |

### Typography

The application uses the platform default UI font. Sizes and weights are fixed by
role; do not set ad hoc font sizes in components.

| Token     | Size | Weight   | Use                          |
| --------- | ---- | -------- | ---------------------------- |
| `caption` | 11px | normal   | Metadata, hints              |
| `body`    | 13px | normal   | Default text and controls    |
| `title`   | 15px | medium   | Section and dialog titles    |
| `heading` | 18px | semibold | Primary headings             |

## Component Specifications

Each component references only tokens. Where a state is not listed, it inherits
the default state.

### Toolbar and Tool Buttons

- Toolbar background `bg.raised`, bottom border `border.subtle`, padding `sm`,
  item spacing `sm`.
- Tool buttons: transparent by default, radius `md`, padding `xs`.
- Hover: background `bg.base`; pressed: background `bg.sunken`.
- Active or checked tab-like buttons: accent text with a subtle accent underline
  or fill; do not use heavy borders.

### Buttons

Two variants only.

- **Primary**: fill `accent`, text `accent.text`, radius `md`, height `md`,
  horizontal padding `md`. Hover `accent.hover`, pressed `accent.pressed`.
  Reserved for the single most important action in a view or dialog (for example
  `OK`, `Add Schedule`).
- **Secondary**: fill `bg.raised`, text `text.primary`, border `border.subtle`,
  radius `md`, height `md`. Hover background lightens toward `border.subtle`,
  border becomes `border.strong`. Used for all other actions (for example
  `Cancel`).

Tool buttons, primary, and secondary buttons must share the same radius and
height rhythm so the interface reads as one system.

### Inputs (Line Edit, Combo Box, Spin Box, Date, Time)

- Background `bg.sunken`, border `border.subtle`, text `text.primary`, radius
  `sm`, padding `xs` to `sm`, height `md`.
- Focus: border `accent`; no glow or drop shadow.
- Combo box popup: background `bg.raised`, selected row uses `accent` background
  with `accent.text`.
- Maintain a minimum width for combo, date, and time controls so labels never
  clip.

### Tables, Trees, and Lists

- Container background `bg.sunken`, border `border.subtle`.
- Header sections: background `bg.raised`, text `text.muted`, bottom border
  `border.subtle`, padding `sm`. Headers are visually distinct from body rows.
- Row selection: background `accent` at reduced emphasis (or a dedicated
  selection surface derived from accent), text remains readable.
- Alternating rows, if used, differ only slightly using `bg.base` against
  `bg.sunken`.
- Empty states: show muted helper text centered in the region rather than a bare
  black rectangle.

### Tabs

- Tab bar sits on `bg.base` with no heavy pane border.
- Selected tab: `accent` text with an accent underline indicator.
- Unselected tab: `text.muted`; hover raises to `text.primary`.

### Progress Bar

- Track: `bg.sunken`, border `border.subtle`, radius `sm`.
- Chunk: `accent`. Use `status.success` on completion and `status.warning` when
  paused if a state color is available.
- Center the percentage text using `text.primary`.

### Scrollbars

Scrollbars must be styled explicitly. The default Qt scrollbars are the primary
source of the dated appearance and must not be left unstyled.

- Width and height: 10px.
- Track: transparent (or `bg.sunken` where a visible groove is needed).
- Handle: `border.strong`, radius `pill` (fully rounded), with a small margin so
  the handle floats inside the track.
- Handle hover: lighten toward `text.muted`.
- Remove the up and down or left and right arrow buttons; set their size to zero.
- No page background on `add-page` or `sub-page` regions.

### Checkboxes, Radios, and Toggles

- Indicator size aligns to control height rhythm; radius `sm` for checkboxes.
- Unchecked: border `border.strong`, background `bg.sunken`.
- Checked: fill `accent`, glyph `accent.text`.
- Status swatches (for example schedule color chips) use `status.*` or the
  configured schedule color and are rendered as rounded squares, not raw
  unstyled boxes.

### Dialogs

- Background `bg.base`, radius `lg` on the window container where the platform
  allows it, internal padding `lg`.
- Title uses the `title` typography token.
- Footer actions are right-aligned with `sm` spacing; the primary action is the
  rightmost button.

### Tooltips

- Background `bg.raised`, text `text.primary`, border `border.subtle`, radius
  `sm`, padding `xs` to `sm`.

## Iconography

Icons are hand-authored, line style, and theme-aware. They are the single icon
vocabulary for the toolbar and tabs, replacing Qt's native standard icons.

- Style: monochrome, stroke-based on a 24x24 grid, 2px stroke, round caps and
  joins. No filled or two-tone glyphs.
- Color: icons are stroked in `text.primary` and re-tinted whenever the theme
  changes, so they read correctly under every theme. Reserve `accent`-colored
  icons for genuinely primary actions.
- Source: authored in-house as SVG path data (no third-party icon dependency)
  and rendered through Qt's SVG renderer at a high-DPI-friendly scale.
- Meaning: each glyph matches its action's behavior (for example a pause glyph
  for pausing, a stop glyph for stop-all, a calendar for the scheduler). Add a
  new glyph rather than reusing an unrelated one.
- Coverage: the toolbar actions, the four main tabs, and the queue-tree entries
  (an accent download-queue glyph and a success-green sync glyph) all use this
  set. The checked checkbox mark is the same line `check` glyph, rendered to a
  cached image because QSS checkbox indicators take a file, not an inline shape.

## Contribution Rules

These rules keep the system intact as the application grows. They are binding for
all interface work.

1. Reference tokens, never literals. Do not introduce a new hex color or ad hoc
   pixel value in a component rule; use an existing token. If no token fits, add
   a token first and justify it.
2. Do not expand the surface or gray palette. Reuse `bg.base`, `bg.raised`, and
   `bg.sunken`.
3. Reserve accent and status colors for meaning, not decoration.
4. Every new widget type gets a rule in the central stylesheet so it inherits the
   system; do not style widgets inline in view code.
5. Any new token must be defined for both concrete themes.
6. Keep spacing, radius, and control heights on the defined scales.
7. When a component's appearance changes, update this document in the same change
   and follow the project versioning and log policies.

## Implementation

The system lives in the `udm/ui/theme/` package:

- `tokens.py`: the `Theme` dataclass and the two concrete theme instances
  (`REFINED_DARK`, `LIGHT`), plus `THEME_OPTIONS` (`System`, `Refined Dark`,
  `Light`), `DEFAULT_THEME` (`System`), `theme_for(name)` (concrete lookup, falls
  back to the default concrete theme), and `resolve_theme(option, dark_preferred)`
  which maps `System` to a concrete theme. This module has no Qt import so tokens
  stay importable from headless code.
- `stylesheet.py`: `build_stylesheet(theme, checkmark_url)` joins the control and
  chrome fragments. This is the only place raw QSS lives.
- `qss_controls.py` / `qss_chrome.py`: the two QSS fragments (core controls, and
  scrollbars/checkboxes/menus/dialog chrome/settings), kept separate so each
  stays small.
- `glyphs.py`: the line-icon SVG data, `render_glyph(name, color, size)`, and the
  `ACTION_GLYPHS` / `TAB_GLYPHS` maps.
- `assets.py`: renders glyphs that QSS must reference by file (the checkbox
  checkmark) into a cache directory and returns their paths.
- `__init__.py`: the public surface, including `stylesheet_for(name)`.

Application and switching:

- The selected option is stored in the `theme` config key (default `System`).
  Existing configuration files gain it automatically through
  `ConfigManager._merge_defaults`.
- `WindowShell.apply_theme(option)` resolves the option (reading the OS scheme via
  `QApplication.styleHints().colorScheme()` for `System`), sets the stylesheet on
  the `QApplication` so open dialogs restyle with the main window, and re-tints
  toolbar and tab icons via `refresh_action_icons`.
- The window subscribes to `QStyleHints.colorSchemeChanged`, so with `System`
  selected the application restyles live when the OS toggles light and dark.
- Options > General exposes a Theme dropdown; accepting Options calls
  `apply_theme` for a live switch with no restart.

Modal layouts:

- The Options dialog uses a left sidebar (`QListWidget#settingsNav`) plus a
  `QStackedWidget` of pages, each with a heading and generous spacing.
- The Scheduler dialog lists schedules in a table with Schedule, Enabled, and
  Actions columns: the enable state is a centered checkbox under the Enabled
  header, and each row shows the schedule name and a plain-language summary.
  Detailed field editing opens in a separate `ScheduleEditorDialog`. Column 0
  stretches and the summary wraps, so the table never scrolls sideways.

- The Options dialog's Browser page (`udm/ui/options_browser_page.py`) holds a
  browser selector, a video-quality selector, a secondary Install Extension
  button, and a muted, word-wrapped status label that lists the remaining
  steps. Shared page and form helpers live in `udm/ui/settings_layout.py`.

Browser extension surfaces:

- The extension popup and the on-video button are web UI and cannot read the
  Qt theme. They mirror the tokens as CSS custom properties with matching names
  (`--bg-base`, `--accent`, `--space-sm`, and so on). The popup follows the
  operating system's light or dark preference through `prefers-color-scheme`.
- The on-video button always uses the Refined Dark surfaces, because it sits on
  arbitrary video frames where a light surface would glare. It is a primary
  accent button at control height `md` with the line `download` glyph, plus a
  compact `sm` close control; its panel uses `bg.base` with `bg.raised` hover
  rows and `status.success` or `status.danger` result text.
- Quality choices reuse the panel and list rows: label in `text.primary`,
  container and size in `text.muted` caption text, and a compact accent
  "< Back" row above them. In the popup they appear in a `card` with a Cancel
  link, and each row's action is a secondary Add button.
- The toolbar badge uses `accent`.

Development hot reload:

- Setting the `UDM_DEV` environment variable enables a file watcher
  (`udm/ui/dev_reload.py`) that reloads the theme modules and re-applies the
  stylesheet and icon tint when a theme file changes, so color and QSS edits
  appear without restarting. Structural layout changes still require a restart.

## Alignment Notes

The gaps that motivated this system are resolved: scrollbars are styled, tool and
push buttons share the button and radius tokens, the surface palette is the three
tokens plus two borders, checkboxes show a themed checkmark, the queue-tree icons
are themed line glyphs, and the Scheduler and Options dialogs follow the card and
sidebar layouts above. Remaining polish, tracked as future work: empty table
regions should present muted helper text rather than a bare rectangle.
