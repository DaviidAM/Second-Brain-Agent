"""
Structured Logging - Phase 7: Observability and Performance
JSON structured logging with contextual fields.
"""

import json
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class LogLevel(Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogContext:
    """Context for structured logging."""

    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    operation: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass
class LogEntry:
    """Structured log entry."""

    timestamp: str
    level: str
    message: str
    context: Optional[LogContext] = None
    error: Optional[str] = None
    stack_trace: Optional[str] = None
    duration_ms: Optional[float] = None
    extra: dict = field(default_factory=dict)


class StructuredLogger:
    """Main structured logger class."""

    def __init__(
        self, name: str = "mcp", level: LogLevel = LogLevel.INFO, output: str = "stdout"
    ):
        self.name = name
        self.level = level
        self.output = output
        self._context = LogContext()

    def set_context(self, context: LogContext):
        """Set logging context."""
        self._context = context

    def _should_log(self, level: LogLevel) -> bool:
        """Check if level should be logged."""
        levels = list(LogLevel)
        return levels.index(level) >= levels.index(self.level)

    def _format_entry(self, entry: LogEntry) -> str:
        """Format log entry as JSON."""
        data = {
            "timestamp": entry.timestamp,
            "level": entry.level,
            "logger": self.name,
            "message": entry.message,
        }

        if entry.context:
            if entry.context.request_id:
                data["request_id"] = entry.context.request_id
            if entry.context.correlation_id:
                data["correlation_id"] = entry.context.correlation_id
            if entry.context.operation:
                data["operation"] = entry.context.operation
            if entry.context.extra:
                data["context"] = entry.context.extra

        if entry.error:
            data["error"] = entry.error

        if entry.stack_trace:
            data["stack_trace"] = entry.stack_trace

        if entry.duration_ms is not None:
            data["duration_ms"] = entry.duration_ms

        if entry.extra:
            data["extra"] = entry.extra

        return json.dumps(data, default=str)

    def _emit(self, entry: LogEntry):
        """Emit log entry."""
        formatted = self._format_entry(entry)

        if self.output == "stdout":
            print(formatted, file=sys.stdout)
        elif self.output == "stderr":
            print(formatted, file=sys.stderr)
        else:
            with open(self.output, "a") as f:
                f.write(formatted + "\n")

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        if not self._should_log(LogLevel.DEBUG):
            return

        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=LogLevel.DEBUG.value,
            message=message,
            context=self._context,
            extra=kwargs,
        )
        self._emit(entry)

    def info(self, message: str, **kwargs):
        """Log info message."""
        if not self._should_log(LogLevel.INFO):
            return

        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=LogLevel.INFO.value,
            message=message,
            context=self._context,
            extra=kwargs,
        )
        self._emit(entry)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        if not self._should_log(LogLevel.WARNING):
            return

        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=LogLevel.WARNING.value,
            message=message,
            context=self._context,
            extra=kwargs,
        )
        self._emit(entry)

    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message."""
        if not self._should_log(LogLevel.ERROR):
            return

        error_msg = str(error) if error else None
        stack = traceback.format_exc() if error else None

        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=LogLevel.ERROR.value,
            message=message,
            context=self._context,
            error=error_msg,
            stack_trace=stack,
            extra=kwargs,
        )
        self._emit(entry)

    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log critical message."""
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=LogLevel.CRITICAL.value,
            message=message,
            context=self._context,
            error=str(error) if error else None,
            stack_trace=traceback.format_exc() if error else None,
            extra=kwargs,
        )
        self._emit(entry)


class RequestLogger:
    """Logger for request/response logging."""

    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger()

    def log_request(
        self,
        method: str,
        path: str,
        query_params: Optional[dict] = None,
        correlation_id: Optional[str] = None,
    ):
        """Log incoming request."""
        self.logger.info(
            f"Request: {method} {path}",
            method=method,
            path=path,
            query_params=query_params or {},
            correlation_id=correlation_id,
        )

    def log_response(
        self,
        status_code: int,
        duration_ms: float,
        correlation_id: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Log outgoing response."""
        level = "info" if status_code < 400 else "warning"

        getattr(self.logger, level)(
            f"Response: {status_code}",
            status_code=status_code,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            error=error,
        )

    def log_slow_request(
        self, method: str, path: str, duration_ms: float, threshold_ms: float = 1000
    ):
        """Log slow request."""
        self.logger.warning(
            f"Slow request: {method} {path}",
            method=method,
            path=path,
            duration_ms=duration_ms,
            threshold_ms=threshold_ms,
            slow=True,
        )
