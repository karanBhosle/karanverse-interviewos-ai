from __future__ import annotations

import logging
from time import perf_counter

logger = logging.getLogger("interviewos.metrics")


class Timer:
    def __init__(self, name: str, **fields: object):
        self.name = name
        self.fields = fields
        self.start = 0.0

    def __enter__(self):
        self.start = perf_counter()
        return self

    def __exit__(self, *_args):
        elapsed_ms = (perf_counter() - self.start) * 1000
        logger.info("metric=%s latency_ms=%.1f fields=%s", self.name, elapsed_ms, self.fields)
