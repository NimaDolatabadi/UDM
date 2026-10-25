"""TLS verification through the operating system's trust store."""

import logging


def use_system_trust():
    """Verify HTTPS with the OS trust store when ``truststore`` is installed.

    The macOS trust store accepts user-installed roots and fetches missing
    intermediate certificates, matching browser behavior for servers that send
    incomplete chains. Returns whether the system store is now in use.
    """
    try:
        import truststore
    except ImportError:
        return False
    try:
        truststore.inject_into_ssl()
    except (OSError, RuntimeError) as error:
        logging.warning("System trust store unavailable: %s", error)
        return False
    return True
