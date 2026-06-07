"""
Operation Logger - Phase 6: Git Automation and Auditability
Structured logging of query, enrich, and write operations.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class OperationType(Enum):
    """Types of operations to log."""

    QUERY = "query"
    ENRICH = "enrich"
    WRITE = "write"
    RETRIEVAL = "retrieval"
    SYNTHESIS = "synthesis"


class OperationStatus(Enum):
    """Status of operations."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class OperationLog:
    """Single operation log entry."""

    operation_id: str
    operation_type: str
    status: str
    timestamp: str
    correlation_id: Optional[str] = None
    user_context: Optional[dict] = None
    request: Optional[dict] = None
    response: Optional[dict] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class LogFormatter:
    """Formats logs for different outputs."""

    def __init__(self, format_type: str = "json"):
        self.format_type = format_type

    def format(self, log: OperationLog) -> str:
        """Format operation log."""
        if self.format_type == "json":
            return self._format_json(log)
        elif self.format_type == "text":
            return self._format_text(log)
        else:
            return self._format_json(log)

    def _format_json(self, log: OperationLog) -> str:
        """Format as JSON."""
        return json.dumps(
            {
                "operation_id": log.operation_id,
                "operation_type": log.operation_type,
                "status": log.status,
                "timestamp": log.timestamp,
                "correlation_id": log.correlation_id,
                "user_context": log.user_context,
                "request": log.request,
                "response": log.response,
                "duration_ms": log.duration_ms,
                "error": log.error,
                "metadata": log.metadata,
            },
            default=str,
        )

    def _format_text(self, log: OperationLog) -> str:
        """Format as human-readable text."""
        lines = [
            f"Operation: {log.operation_type}",
            f"ID: {log.operation_id}",
            f"Status: {log.status}",
            f"Timestamp: {log.timestamp}",
        ]

        if log.correlation_id:
            lines.append(f"Correlation ID: {log.correlation_id}")

        if log.duration_ms:
            lines.append(f"Duration: {log.duration_ms:.2f}ms")

        if log.error:
            lines.append(f"Error: {log.error}")

        return "\n".join(lines)


class AuditTrail:
    """Manages audit trail persistence."""

    def __init__(self, audit_dir: str = ".metadata/audit"):
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def write(self, log: OperationLog):
        """Write log to audit trail."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        file_path = self.audit_dir / f"audit_{date_str}.jsonl"

        with open(file_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "operation_id": log.operation_id,
                        "operation_type": log.operation_type,
                        "status": log.status,
                        "timestamp": log.timestamp,
                        "correlation_id": log.correlation_id,
                        "duration_ms": log.duration_ms,
                        "error": log.error,
                    },
                    default=str,
                )
                + "\n"
            )

    def query(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        operation_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[OperationLog]:
        """Query audit trail."""
        logs = []

        pattern = "audit_*.jsonl"
        for file_path in sorted(self.audit_dir.glob(pattern), reverse=True)[:10]:
            if start_date and file_path.stem < f"audit_{start_date}":
                continue
            if end_date and file_path.stem > f"audit_{end_date}":
                continue

            with open(file_path) as f:
                for line in f:
                    try:
                        entry = json.loads(line)

                        if (
                            operation_type
                            and entry.get("operation_type") != operation_type
                        ):
                            continue
                        if (
                            correlation_id
                            and entry.get("correlation_id") != correlation_id
                        ):
                            continue

                        logs.append(
                            OperationLog(
                                operation_id=entry.get("operation_id", ""),
                                operation_type=entry.get("operation_type", ""),
                                status=entry.get("status", ""),
                                timestamp=entry.get("timestamp", ""),
                                correlation_id=entry.get("correlation_id"),
                                duration_ms=entry.get("duration_ms"),
                                error=entry.get("error"),
                            )
                        )

                        if len(logs) >= limit:
                            return logs

                    except json.JSONDecodeError:
                        continue

        return logs


class OperationLogger:
    """
    Main operation logger for structured logging.
    """

    def __init__(
        self,
        audit_dir: str = ".metadata/audit",
        log_format: str = "json",
        log_level: str = "INFO",
    ):
        self.audit_trail = AuditTrail(audit_dir)
        self.formatter = LogFormatter(log_format)
        self.log_level = log_level
        self._active_operations: dict[str, OperationLog] = {}

    def log_operation(
        self,
        operation_type: OperationType,
        request: Optional[dict] = None,
        correlation_id: Optional[str] = None,
        user_context: Optional[dict] = None,
    ) -> str:
        """Start logging an operation."""
        operation_id = str(uuid.uuid4())

        log = OperationLog(
            operation_id=operation_id,
            operation_type=operation_type.value,
            status=OperationStatus.STARTED.value,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=correlation_id,
            user_context=user_context,
            request=request,
        )

        self._active_operations[operation_id] = log

        return operation_id

    def complete_operation(
        self,
        operation_id: str,
        response: Optional[dict] = None,
        error: Optional[str] = None,
    ):
        """Mark operation as completed."""
        if operation_id not in self._active_operations:
            return

        log = self._active_operations[operation_id]

        start_time = datetime.fromisoformat(log.timestamp)
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000

        log.status = (
            OperationStatus.COMPLETED.value
            if not error
            else OperationStatus.FAILED.value
        )
        log.response = response
        log.error = error
        log.duration_ms = duration

        self._write_log(log)
        del self._active_operations[operation_id]

    def log_query(
        self,
        query: str,
        correlation_id: Optional[str] = None,
        response: Optional[dict] = None,
        duration_ms: Optional[float] = None,
    ):
        """Log a query operation."""
        log = OperationLog(
            operation_id=str(uuid.uuid4()),
            operation_type=OperationType.QUERY.value,
            status=OperationStatus.COMPLETED.value,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=correlation_id,
            request={"query": query},
            response=response,
            duration_ms=duration_ms,
        )

        self._write_log(log)

    def log_enrichment(
        self,
        correlation_id: str,
        gaps_detected: int,
        gaps_filled: int,
        files_written: list[str],
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
    ):
        """Log an enrichment operation."""
        log = OperationLog(
            operation_id=str(uuid.uuid4()),
            operation_type=OperationType.ENRICH.value,
            status=OperationStatus.FAILED.value
            if error
            else OperationStatus.COMPLETED.value,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=correlation_id,
            request={
                "gaps_detected": gaps_detected,
                "gaps_filled": gaps_filled,
                "files_written": files_written,
            },
            duration_ms=duration_ms,
            error=error,
        )

        self._write_log(log)

    def log_write(
        self,
        file_path: str,
        correlation_id: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """Log a write operation."""
        log = OperationLog(
            operation_id=str(uuid.uuid4()),
            operation_type=OperationType.WRITE.value,
            status=OperationStatus.COMPLETED.value
            if success
            else OperationStatus.FAILED.value,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=correlation_id,
            request={"file_path": file_path},
            error=error,
        )

        self._write_log(log)

    def _write_log(self, log: OperationLog):
        """Write log to output."""
        formatted = self.formatter.format(log)

        if self.log_level != "SILENT":
            print(formatted)

        self.audit_trail.write(log)

    def get_operation(self, operation_id: str) -> Optional[OperationLog]:
        """Get active operation by ID."""
        return self._active_operations.get(operation_id)

    def get_recent_operations(
        self, operation_type: Optional[str] = None, limit: int = 10
    ) -> list[OperationLog]:
        """Get recent operations."""
        return self.audit_trail.query(limit=limit, operation_type=operation_type)

    def get_operations_by_correlation(self, correlation_id: str) -> list[OperationLog]:
        """Get all operations for a correlation ID."""
        return self.audit_trail.query(correlation_id=correlation_id, limit=100)
