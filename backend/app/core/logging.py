import logging
import re
import sys

SECRET_PATTERNS = (
    re.compile(r"(api[_-]?key|authorization|bearer|secret|token|password)\s*[:=]\s*([^\s,;]+)", re.I),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.I),
)


def redact(text: str) -> str:
    redacted = SECRET_PATTERNS[0].sub(r"\1=***REDACTED***", text)
    redacted = SECRET_PATTERNS[1].sub("sk-***REDACTED***", redacted)
    return SECRET_PATTERNS[2].sub("Bearer ***REDACTED***", redacted)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return redact(message)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        RedactingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
