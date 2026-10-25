"""Compatibility entry point for Umbrella Download Manager.

``--native-messaging-host`` runs the browser bridge host instead of the GUI.
It is dispatched before any Qt import so the host starts quickly and writes
nothing but protocol frames to stdout.
"""

import sys

HOST_FLAG = "--native-messaging-host"
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
    from udm.app import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_run())
