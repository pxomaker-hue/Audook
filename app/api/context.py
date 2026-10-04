"""Lazily-initialised services shared by every blueprint.

Filled in by audook_backend.init_services on the first real request (not at
import time, so /health answers before the heavy services are up).
"""


class _Services:
    library = None
    player = None
    sync = None


services = _Services()
