"""
Provenance Tracking - Phase 6: Git Automation and Auditability
Tracks correlation IDs and lineage across request lifecycle.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ProvenanceRecord:
    """Record of provenance for a piece of content."""

    correlation_id: str
    source_query: str
    enrichment_triggered: bool
    llm_model: Optional[str] = None
    generation_time: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    original_sources: list[str] = field(default_factory=list)
    enriched_content_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class LineageEntry:
    """Entry in content lineage."""

    timestamp: str
    event: str
    correlation_id: str
    details: dict = field(default_factory=dict)


class CorrelationManager:
    """Manages correlation IDs across requests."""

    def __init__(self):
        self._correlations: dict[str, dict] = {}

    def create_correlation_id(self, query: str) -> str:
        """Create new correlation ID for a query."""
        correlation_id = str(uuid.uuid4())

        self._correlations[correlation_id] = {
            "query": query,
            "created_at": datetime.utcnow().isoformat(),
            "events": [],
        }

        return correlation_id

    def get_correlation(self, correlation_id: str) -> Optional[dict]:
        """Get correlation data."""
        return self._correlations.get(correlation_id)

    def add_event(
        self, correlation_id: str, event: str, details: Optional[dict] = None
    ):
        """Add event to correlation."""
        if correlation_id not in self._correlations:
            return

        self._correlations[correlation_id]["events"].append(
            {
                "event": event,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details or {},
            }
        )

    def get_events(self, correlation_id: str) -> list[dict]:
        """Get all events for correlation."""
        correlation = self.get_correlation(correlation_id)
        if correlation:
            return correlation.get("events", [])
        return []

    def link_enrichment(
        self,
        correlation_id: str,
        llm_model: str,
        generation_time: float,
        files_written: list[str],
    ):
        """Link enrichment to correlation."""
        if correlation_id not in self._correlations:
            return

        self._correlations[correlation_id].update(
            {
                "enrichment_triggered": True,
                "llm_model": llm_model,
                "generation_time": generation_time,
                "files_written": files_written,
            }
        )


class LineageRecorder:
    """Records lineage of content changes."""

    def __init__(self, lineage_dir: str = ".metadata/lineage"):
        self.lineage_dir = Path(lineage_dir)
        self.lineage_dir.mkdir(parents=True, exist_ok=True)

    def record(self, correlation_id: str, event: str, details: Optional[dict] = None):
        """Record lineage entry."""
        entry = LineageEntry(
            timestamp=datetime.utcnow().isoformat(),
            event=event,
            correlation_id=correlation_id,
            details=details or {},
        )

        file_path = self.lineage_dir / f"{correlation_id}.jsonl"

        with open(file_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": entry.timestamp,
                        "event": entry.event,
                        "correlation_id": entry.correlation_id,
                        "details": entry.details,
                    }
                )
                + "\n"
            )

    def get_lineage(self, correlation_id: str) -> list[LineageEntry]:
        """Get lineage for correlation ID."""
        file_path = self.lineage_dir / f"{correlation_id}.jsonl"

        if not file_path.exists():
            return []

        entries = []

        with open(file_path) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    entries.append(
                        LineageEntry(
                            timestamp=data["timestamp"],
                            event=data["event"],
                            correlation_id=data["correlation_id"],
                            details=data.get("details", {}),
                        )
                    )
                except json.JSONDecodeError:
                    continue

        return entries

    def get_content_lineage(self, content_path: str) -> list[dict]:
        """Get lineage for a specific content file."""
        path_str = str(content_path)

        lineage = []

        for file_path in self.lineage_dir.glob("*.jsonl"):
            with open(file_path) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        details = data.get("details", {})

                        if details.get("file_path") == path_str:
                            lineage.append(data)
                    except json.JSONDecodeError:
                        continue

        return sorted(lineage, key=lambda x: x.get("timestamp", ""))


class ProvenanceTracker:
    """
    Main provenance tracking class.
    """

    def __init__(
        self,
        lineage_dir: str = ".metadata/lineage",
        provenance_dir: str = ".metadata/provenance",
    ):
        self.correlation_manager = CorrelationManager()
        self.lineage_recorder = LineageRecorder(lineage_dir)

        self.provenance_dir = Path(provenance_dir)
        self.provenance_dir.mkdir(parents=True, exist_ok=True)

    def start_request(self, query: str) -> str:
        """Start tracking a new request."""
        correlation_id = self.correlation_manager.create_correlation_id(query)

        self.lineage_recorder.record(
            correlation_id=correlation_id,
            event="request_started",
            details={"query": query},
        )

        return correlation_id

    def record_retrieval(
        self, correlation_id: str, sources: list[str], confidence: float
    ):
        """Record retrieval results."""
        self.correlation_manager.add_event(
            correlation_id,
            "retrieval_completed",
            {"sources": sources, "confidence": confidence},
        )

        self.lineage_recorder.record(
            correlation_id=correlation_id,
            event="retrieval_completed",
            details={"sources": sources, "confidence": confidence},
        )

    def record_enrichment(
        self,
        correlation_id: str,
        gaps_detected: int,
        llm_model: str,
        generation_time: float,
        files_written: list[str],
    ):
        """Record enrichment results."""
        self.correlation_manager.link_enrichment(
            correlation_id, llm_model, generation_time, files_written
        )

        self.lineage_recorder.record(
            correlation_id=correlation_id,
            event="enrichment_completed",
            details={
                "gaps_detected": gaps_detected,
                "llm_model": llm_model,
                "generation_time": generation_time,
                "files_written": files_written,
            },
        )

    def record_write(self, correlation_id: str, file_path: str, success: bool = True):
        """Record write operation."""
        self.correlation_manager.add_event(
            correlation_id,
            "write_completed" if success else "write_failed",
            {"file_path": file_path, "success": success},
        )

        self.lineage_recorder.record(
            correlation_id=correlation_id,
            event="write_completed" if success else "write_failed",
            details={"file_path": file_path, "success": success},
        )

    def record_synthesis(
        self, correlation_id: str, response_length: int, citations_count: int
    ):
        """Record synthesis results."""
        self.correlation_manager.add_event(
            correlation_id,
            "synthesis_completed",
            {"response_length": response_length, "citations_count": citations_count},
        )

        self.lineage_recorder.record(
            correlation_id=correlation_id,
            event="synthesis_completed",
            details={
                "response_length": response_length,
                "citations_count": citations_count,
            },
        )

    def finalize_request(self, correlation_id: str, success: bool = True):
        """Finalize request tracking."""
        self.lineage_recorder.record(
            correlation_id=correlation_id,
            event="request_completed" if success else "request_failed",
            details={"success": success},
        )

    def get_provenance(self, correlation_id: str) -> Optional[ProvenanceRecord]:
        """Get complete provenance record."""
        correlation = self.correlation_manager.get_correlation(correlation_id)

        if not correlation:
            return None

        events = self.correlation_manager.get_events(correlation_id)

        return ProvenanceRecord(
            correlation_id=correlation_id,
            source_query=correlation.get("query", ""),
            enrichment_triggered=correlation.get("enrichment_triggered", False),
            llm_model=correlation.get("llm_model"),
            generation_time=correlation.get("generation_time"),
            original_sources=[],
            metadata={"events": events},
        )

    def get_lineage(self, correlation_id: str) -> list[LineageEntry]:
        """Get lineage for correlation ID."""
        return self.lineage_recorder.get_lineage(correlation_id)

    def search_by_content(self, content_path: str) -> list[dict]:
        """Search provenance by content path."""
        return self.lineage_recorder.get_content_lineage(content_path)
