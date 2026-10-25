"""Background worker threads.

Exports resolve lazily so Qt-free helpers in this package (option builders,
the format probe) can be imported by the native host without loading Qt.
"""

_EXPORTS = {
    "BulkSpiderWorker": "udm.workers.spiders",
    "DownloadWorker": "udm.workers.download",
    "SpiderWorker": "udm.workers.spiders",
    "StreamWorker": "udm.workers.stream",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    from importlib import import_module

    return getattr(import_module(_EXPORTS[name]), name)
