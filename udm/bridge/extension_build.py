"""Assemble a loadable browser extension for one browser engine.

The source in ``extension/`` holds shared scripts plus a base manifest and a
per-engine overlay. Chromium needs a service worker and a fixed public key;
Firefox needs background scripts and a Gecko add-on ID; Safari needs
background scripts, drops the APIs it lacks, and adds link-click capture.
"""

import base64
import hashlib
import json
from pathlib import Path
import shutil

from udm import paths

_SOURCE_PARTS = ("src", "icons")


def source_dir():
    """Return the extension source directory for this run."""
    return paths.resource_path("extension")


def load_manifest(engine, source=None):
    """Return the merged manifest for ``engine`` (see ``udm.bridge.browsers``).

    Overlay keys replace base keys, except ``permissions``, which the overlay
    extends so an engine can add permissions the others reject, and
    ``exclude_permissions``, which removes base permissions the engine lacks.
    """
    source = Path(source or source_dir())
    manifest = _read_json(source / "manifest.base.json")
    overlay = _read_json(source / f"manifest.{engine}.json")
    extra = overlay.pop("permissions", [])
    excluded = set(overlay.pop("exclude_permissions", []))
    manifest.update(overlay)
    manifest["permissions"] = [
        name for name in manifest.get("permissions", []) + extra if name not in excluded
    ]
    return manifest


def build_extension(engine, destination, version, source=None):
    """Write an unpacked extension for ``engine`` into ``destination``.

    The destination is replaced so a reinstall after an app update never mixes
    old and new scripts. Returns the destination path.
    """
    source = Path(source or source_dir())
    destination = Path(destination)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for item in (source / "src").iterdir():
        if item.is_file():
            shutil.copy2(item, destination / item.name)
    shutil.copytree(source / "icons", destination / "icons")
    manifest = load_manifest(engine, source)
    manifest["version"] = version
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return destination


def chromium_extension_id(source=None):
    """Return the Chromium extension ID derived from the manifest public key.

    Chromium hashes the DER public key with SHA-256 and maps the first 32 hex
    digits onto the letters ``a`` to ``p``.
    """
    key = load_manifest("chromium", source)["key"]
    digest = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32]
    return "".join(chr(ord("a") + int(char, 16)) for char in digest)


def firefox_extension_id(source=None):
    """Return the Gecko add-on ID declared in the Firefox overlay."""
    manifest = load_manifest("firefox", source)
    return manifest["browser_specific_settings"]["gecko"]["id"]


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
