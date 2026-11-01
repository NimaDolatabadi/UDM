"""Package the extension as standalone release files.

``python -m udm.bridge.extension_package [dist]`` writes
``udm-capture-chromium-<version>.zip`` and ``udm-capture-firefox-<version>.xpi``
into ``dist`` (default ``dist/``). Both are built by
:func:`udm.bridge.extension_build.build_extension`, so they hold exactly what
the app's developer install writes for the same version. Archives are
reproducible: entries are sorted and carry a fixed timestamp and mode.
"""

from pathlib import Path
import sys
import tempfile
import zipfile

from udm import __version__
from udm.bridge import extension_build
from udm.bridge.browsers import CHROMIUM, FIREFOX

# Covers Chrome, Edge, Brave, Vivaldi, Opera, Arc, and Chromium.
ARTIFACT_NAMES = {
    CHROMIUM: "udm-capture-chromium-{version}.zip",
    FIREFOX: "udm-capture-firefox-{version}.xpi",
}
# ZIP cannot store dates before 1980; a fixed date keeps builds identical.
_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def artifact_name(engine, version):
    """Return the release file name for ``engine``."""
    return ARTIFACT_NAMES[engine].format(version=version)


def package(engine, dist_dir, version=None, source=None):
    """Build the extension for ``engine`` and archive it; return the file path.

    The manifest sits at the archive root, as browsers and stores expect.
    """
    version = version or __version__
    dist_dir = Path(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)
    target = dist_dir / artifact_name(engine, version)
    with tempfile.TemporaryDirectory() as temp:
        built = extension_build.build_extension(
            engine, Path(temp) / engine, version, source
        )
        write_archive(built, target)
    return target


def package_all(dist_dir, version=None, source=None):
    """Write every release file; return their paths."""
    return [package(engine, dist_dir, version, source) for engine in ARTIFACT_NAMES]


def write_archive(folder, target):
    """Write ``folder``'s files into a reproducible ZIP archive at ``target``."""
    folder = Path(folder)
    files = sorted(path for path in folder.rglob("*") if path.is_file())
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            entry = zipfile.ZipInfo(path.relative_to(folder).as_posix(), _TIMESTAMP)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, path.read_bytes())
    return target


def main(argv=None):
    """Write the release files and print their paths; return an exit code."""
    argv = sys.argv[1:] if argv is None else argv
    for path in package_all(argv[0] if argv else "dist"):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
