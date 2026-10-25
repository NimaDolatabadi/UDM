"""Human-readable transfer rate and duration text shared by workers."""


def format_rate(bytes_per_second):
    """Return a rate such as ``1.5 MB/s``."""
    value = float(bytes_per_second or 0)
    for unit in ("B/s", "KB/s", "MB/s"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB/s"


def format_duration(seconds):
    """Return ``HH:MM:SS``, or ``--`` when the duration is unknown."""
    if seconds is None:
        return "--"
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
