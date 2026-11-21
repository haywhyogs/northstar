"""Graceful shutdown: Kubernetes sends SIGTERM before stopping a pod; Ctrl+C sends SIGINT locally."""

import signal
import threading

stop_requested = threading.Event()


def install_signal_handlers() -> None:
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop_requested.set())
