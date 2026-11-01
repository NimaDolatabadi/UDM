"""Headless check that a packaged build is complete.

``UDM --self-check`` imports every ``udm`` module and confirms the bundled
resources are present, then exits without opening a window. CI runs it on the
freshly built app, so a missing hidden import or data file fails the pull
request instead of the release.
"""

import importlib
import pkgutil
import sys
import tempfile
import traceback

import udm
from udm import paths

# Modules that must be found, so an importer that lists nothing cannot pass.
_REQUIRED_MODULES = ("udm.app", "udm.ui.main_window", "udm.bridge.native_host")


def module_names():
    """Return the names of every module in the ``udm`` package."""
    # A package that fails to import is still listed, so check_imports
    # reports it.
    found = pkgutil.walk_packages(udm.__path__, prefix="udm.", onerror=lambda name: None)
    return sorted(info.name for info in found)


def check_imports(names=None, importer=importlib.import_module):
    """Import each module; return ``(name, error)`` pairs for the failures."""
    names = module_names() if names is None else names
    failures = []
    missing = [name for name in _REQUIRED_MODULES if name not in names]
    if missing:
        failures.append(("module list", f"not found: {', '.join(missing)}"))
    for name in names:
        try:
            importer(name)
        except Exception:  # Report every broken module, not only the first.
            failures.append((name, traceback.format_exc(limit=3)))
    return failures


def check_resources():
    """Return descriptions of missing bundled resources."""
    from udm.bridge import extension_build, safari
    from udm.bridge.browsers import CHROMIUM, FIREFOX, SAFARI

    problems = []
    for relative in ("VERSION", "logo.png", "extension/manifest.base.json"):
        if not paths.resource_path(*relative.split("/")).is_file():
            problems.append(f"missing resource: {relative}")
    with tempfile.TemporaryDirectory() as temp:
        for engine in (CHROMIUM, FIREFOX, SAFARI):
            try:
                extension_build.build_extension(engine, f"{temp}/{engine}", udm.__version__)
            except (OSError, ValueError, KeyError) as error:
                problems.append(f"extension build failed for {engine}: {error}")
    # Users without developer tools rely on the precompiled Safari binaries.
    if paths.is_frozen() and sys.platform == "darwin" and not safari.bundled_binaries():
        problems.append("missing resource: safari-bin")
    return problems


def run(stream=None):
    """Run every check, report to ``stream``, and return an exit code."""
    stream = stream or sys.stderr
    failures = check_imports()
    problems = check_resources()
    for name, error in failures:
        print(f"import failed: {name}\n{error}", file=stream)
    for problem in problems:
        print(problem, file=stream)
    if failures or problems:
        print("UDM self-check failed", file=stream)
        return 1
    print(f"UDM {udm.__version__} self-check passed ({len(module_names())} modules)",
          file=stream)
    return 0
