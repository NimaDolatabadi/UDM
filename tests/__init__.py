"""UDM test suite."""

import os
import tempfile

# Keep every test away from the real per-user data directory and its socket.
os.environ.setdefault("UDM_DATA_DIR", tempfile.mkdtemp(prefix="udm-test-data-"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
