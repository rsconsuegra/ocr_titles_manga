"""Container healthcheck for the Dramatiq worker.

The worker is a process, not an HTTP server, so it cannot reuse the API's
HTTP healthcheck baked into the image. This probe verifies the dramatiq
process is running by scanning ``/proc`` (works on the slim image, which has
no ``pgrep``).
"""

from __future__ import annotations

import os
import sys


def _dramatiq_running() -> bool:
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/cmdline", "rb") as fh:
                if b"dramatiq" in fh.read():
                    return True
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return False


def main() -> int:
    return 0 if _dramatiq_running() else 1


if __name__ == "__main__":
    raise SystemExit(main())
