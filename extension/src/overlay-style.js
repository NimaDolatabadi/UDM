/* Shadow-DOM stylesheet for the on-video download button and panel. */
"use strict";

// Values mirror the design tokens in docs/design-system.md. The overlay sits
// on arbitrary video content, so it always uses the Refined Dark surfaces.
const UDM_OVERLAY_CSS = `
:host {
  all: initial;
  --bg-base: #1c1e22;
  --bg-raised: #26292e;
  --border-subtle: #2f333a;
  --border-strong: #3d424b;
  --text-primary: #e6e8eb;
  --text-muted: #9aa2ad;
  --accent: #2f81f7;
  --accent-hover: #4c94f8;
  --accent-text: #ffffff;
  --status-success: #2ea043;
  --status-danger: #f85149;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --radius-sm: 4px;
  --radius-md: 6px;
  --control-sm: 24px;
  --control-md: 30px;
  position: fixed;
  z-index: 2147483647;
  font: 13px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--text-primary);
}
.wrap { display: flex; flex-direction: column; align-items: flex-end; gap: var(--space-xs); }
.trigger {
  display: inline-flex; align-items: center; gap: var(--space-xs);
  height: var(--control-md); padding: 0 var(--space-md);
  border: 1px solid var(--accent); border-radius: var(--radius-md);
  background: var(--accent); color: var(--accent-text);
  font: inherit; font-weight: 600; cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
}
.trigger:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
.trigger svg { width: 16px; height: 16px; }
.close {
  width: var(--control-sm); height: var(--control-sm);
  border: 1px solid var(--border-strong); border-radius: var(--radius-md);
  background: var(--bg-raised); color: var(--text-muted); cursor: pointer;
  font: inherit; line-height: 1;
}
.row { display: flex; gap: var(--space-xs); align-items: center; }
.panel {
  width: 300px; max-height: 320px; overflow-y: auto;
  background: var(--bg-base); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); padding: var(--space-xs);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
}
.panel[hidden] { display: none; }
.item {
  display: block; width: 100%; text-align: left;
  padding: var(--space-sm); border: none; border-radius: var(--radius-sm);
  background: transparent; color: var(--text-primary);
  font: inherit; cursor: pointer;
}
.item:hover { background: var(--bg-raised); }
.item.back { color: var(--accent); font-size: 11px; padding: var(--space-xs) var(--space-sm); }
.name { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meta { display: block; color: var(--text-muted); font-size: 11px; }
.message { padding: var(--space-sm); color: var(--text-muted); font-size: 11px; }
.message.ok { color: var(--status-success); }
.message.error { color: var(--status-danger); }
`;
