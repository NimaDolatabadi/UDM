"""Compatibility entry point for Umbrella Download Manager.

``--native-messaging-host`` runs the browser bridge host instead of the GUI.
It is dispatched before any Qt import so the host starts quickly and writes
nothing but protocol frames to stdout. ``--self-check`` verifies a packaged
build without opening a window (``udm.self_check``).
"""

import sys

HOST_FLAG = "--native-messaging-host"
SELF_CHECK_FLAG = "--self-check"
__all__ = ["MainWindow", "UDMManager", "main"]


def __getattr__(name):
    # Lazy re-exports keep ``import MACDM`` compatible without loading Qt early.
    if name in ("MainWindow", "UDMManager"):
        from udm.ui import main_window

        return getattr(main_window, name)
    if name == "main":
        from udm.app import main

        return main
    raise AttributeError(name)


def _run():
    if HOST_FLAG in sys.argv:
        from udm.bridge.native_host import main as host_main

        return host_main()
    if SELF_CHECK_FLAG in sys.argv:
        from udm.self_check import run

        return run()
    from udm.app import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_run())
