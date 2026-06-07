"""
Enrichment Orchestrator - Phase 4: Write and Enrichment Pipeline
Coordinates the complete enrichment workflow.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .enrichment_client import EnrichmentClient
from .gap_detector import GapDetector
from .merge_engine import MergeEngine, MergeStrategy
from .write_manager import WriteManager, WriteMode, WriteOperation


class EnrichmentStatus(Enum):
    """Status of enrichment operation."""

    IDLE = "idle"
    DETECTING_GAPS = "detecting_gaps"
    CALLING_LLM = "calling_llm"
    VALIDATING = "validating"
    MERGING = "merging"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class EnrichmentContext:
    """Context for enrichment operation."""

    query: str
    confidence_score: float
    retrieved_sources: list[dict]
    context_summary: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class EnrichmentState:
    """Tracks state of enrichment operation."""

    status: EnrichmentStatus = EnrichmentStatus.IDLE
    correlation_id: str = ""
    gaps_detected: int = 0
    llm_calls_made: int = 0
    validation_failures: int = 0
    writes_completed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "correlation_id": self.correlation_id,
            "gaps_detected": self.gaps_detected,
            "llm_calls_made": self.llm_calls_made,
            "validation_failures": self.validation_failures,
            "writes_completed": self.writes_completed,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class EnrichmentResult:
    """Result of enrichment operation."""

    success: bool
    enrichment_triggered: bool
    gaps_filled: int
    state: EnrichmentState
    new_content_paths: list[str] = field(default_factory=list)
    error: Optional[str] = None


class EnrichmentOrchestrator:
    """
    Orchestrates the complete enrichment workflow:
    gap detection → LLM call → validation → merge → write
    """

    def __init__(
        self,
        gap_detector: Optional[GapDetector] = None,
        enrichment_client: Optional[EnrichmentClient] = None,
        merge_engine: Optional[MergeEngine] = None,
        write_manager: Optional[WriteManager] = None,
        enable_writes: bool = True,
        wiki_path: str = "knowledge/wiki",
    ):
        self.gap_detector = gap_detector or GapDetector()
        self.enrichment_client = enrichment_client
        self.merge_engine = merge_engine or MergeEngine()
        self.write_manager = write_manager or WriteManager()
        self.enable_writes = enable_writes
        self.wiki_path = wiki_path

    def enrich(
        self,
        context: EnrichmentContext,
        existing_contents: Optional[dict[str, str]] = None,
    ) -> EnrichmentResult:
        """
        Execute complete enrichment workflow.

        Args:
            context: Enrichment context with query and retrieval info
            existing_contents: Optional dict of existing file contents

        Returns:
            EnrichmentResult with operation status
        """
        state = EnrichmentState(
            correlation_id=context.correlation_id, started_at=self._get_timestamp()
        )

        if not self.enrichment_client or not self.enrichment_client.is_configured():
            state.status = EnrichmentStatus.SKIPPED
            state.warnings.append("LLM client not configured, skipping enrichment")
            return EnrichmentResult(
                success=True,
                enrichment_triggered=False,
                gaps_filled=0,
                state=state,
                error="LLM client not configured",
            )

        state.status = EnrichmentStatus.DETECTING_GAPS
        gap_analysis = self.gap_detector.detect_gaps(
            query=context.query,
            confidence_score=context.confidence_score,
            retrieved_sources=context.retrieved_sources,
            context_summary=context.context_summary,
        )

        if not gap_analysis.requires_enrichment:
            state.status = EnrichmentStatus.SKIPPED
            state.completed_at = self._get_timestamp()
            return EnrichmentResult(
                success=True, enrichment_triggered=False, gaps_filled=0, state=state
            )

        state.gaps_detected = gap_analysis.total_gaps
        prioritized_gaps = gap_analysis.get_prioritized_gaps()

        gaps_filled = 0
        new_paths = []
        existing_contents = existing_contents or {}

        for gap in prioritized_gaps:
            if gap.priority.value > 2:
                continue

            result = self._process_gap(gap, context, existing_contents, state)

            if result:
                gaps_filled += 1
                new_paths.append(result)

        state.status = EnrichmentStatus.COMPLETED
        state.completed_at = self._get_timestamp()
        state.writes_completed = gaps_filled

        return EnrichmentResult(
            success=True,
            enrichment_triggered=gaps_filled > 0,
            gaps_filled=gaps_filled,
            state=state,
            new_content_paths=new_paths,
        )

    def _process_gap(
        self,
        gap,
        context: EnrichmentContext,
        existing_contents: dict[str, str],
        state: EnrichmentState,
    ) -> Optional[str]:
        """Process a single gap through the enrichment pipeline."""
        state.status = EnrichmentStatus.CALLING_LLM

        try:
            response, validation = self.enrichment_client.enrich(
                gap_type=gap.gap_type.value,
                topic=gap.topic,
                query_context=gap.description,
                existing_sources=gap.source_documents,
            )

            state.llm_calls_made += 1

        except Exception as e:
            state.errors.append(f"LLM call failed: {e}")
            state.status = EnrichmentStatus.FAILED
            return None

        state.status = EnrichmentStatus.VALIDATING

        if not validation.is_valid:
            state.validation_failures += 1
            state.warnings.extend(validation.errors)
            return None

        state.status = EnrichmentStatus.MERGING

        file_path = self._generate_file_path(gap.topic)
        existing_content = existing_contents.get(file_path, "")

        merge_result = self.merge_engine.merge(
            new_content=response.content,
            existing_content=existing_content,
            strategy=MergeStrategy.APPEND,
            title=gap.topic,
        )

        if not merge_result.success:
            state.errors.append(f"Merge failed: {merge_result.error}")
            return None

        if not self.enable_writes:
            state.status = EnrichmentStatus.COMPLETED
            return file_path

        state.status = EnrichmentStatus.WRITING

        operation = WriteOperation(
            path=file_path,
            content=merge_result.merged_content,
            mode=WriteMode.CREATE if not existing_content else WriteMode.UPDATE,
            title=gap.topic,
            correlation_id=context.correlation_id,
            frontmatter={
                "title": gap.topic,
                "source_type": "enrichment",
                "gap_type": gap.gap_type.value,
                "enrichment_rationale": gap.suggested_approach or "",
            },
        )

        write_result = self.write_manager.write(operation)

        if write_result.success:
            return file_path
        else:
            state.errors.append(f"Write failed: {write_result.error}")
            return None

    def _generate_file_path(self, topic: str) -> str:
        """Generate file path from topic."""
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic)
        safe_name = safe_name.strip().replace(" ", "_").lower()
        return f"{self.wiki_path}/{safe_name}.md"

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.utcnow().isoformat()

    def get_state(self) -> EnrichmentState:
        """Get current enrichment state."""
        return EnrichmentState()

    def reset_state(self):
        """Reset enrichment state."""
        pass


class EnrichmentStateTracker:
    """Tracks enrichment state across requests."""

    def __init__(self):
        self._states: dict[str, EnrichmentState] = {}

    def create_state(self, correlation_id: str) -> EnrichmentState:
        """Create new state for correlation ID."""
        state = EnrichmentState(correlation_id=correlation_id)
        self._states[correlation_id] = state
        return state

    def get_state(self, correlation_id: str) -> Optional[EnrichmentState]:
        """Get state for correlation ID."""
        return self._states.get(correlation_id)

    def update_state(self, correlation_id: str, state: EnrichmentState):
        """Update state for correlation ID."""
        self._states[correlation_id] = state

    def remove_state(self, correlation_id: str):
        """Remove state for correlation ID."""
        self._states.pop(correlation_id, None)

    def get_all_states(self) -> dict[str, EnrichmentState]:
        """Get all tracked states."""
        return self._states.copy()
