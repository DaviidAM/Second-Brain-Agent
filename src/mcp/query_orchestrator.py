"""
Query Orchestrator - Phase 5: AI Response Generation and Safety Controls
Coordinates retrieval, confidence assessment, synthesis, and citation flow.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .context_builder import ContextBuilder
from .gap_detector import GapAnalysis, GapDetector
from .query_analyzer import QueryAnalyzer
from .repository import KnowledgeRepository
from .retrieval import RetrievalOrchestrator


class ConfidenceLevel(Enum):
    """Confidence levels for responses."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class ConfidenceThreshold:
    """Thresholds for confidence levels."""

    high: float = 0.9
    medium: float = 0.7
    low: float = 0.5


@dataclass
class QueryResponse:
    """Structured response following API contract."""

    ok: bool
    response: str
    sources: list[dict] = field(default_factory=list)
    confidence: float
    confidence_level: str
    gaps_detected: list[dict] = field(default_factory=list)
    enrichment_triggered: bool = False
    request_id: str = ""
    error: Optional[str] = None


class ConfidenceAssessor:
    """Assesses confidence level from retrieval results."""

    def __init__(self, thresholds: Optional[ConfidenceThreshold] = None):
        self.thresholds = thresholds or ConfidenceThreshold()

    def assess(
        self,
        confidence_score: float,
        gap_analysis: Optional[GapAnalysis] = None,
        source_count: int = 0,
    ) -> tuple[float, ConfidenceLevel]:
        """
        Assess confidence level.

        Returns:
            Tuple of (adjusted_confidence, confidence_level)
        """
        adjusted = confidence_score

        if gap_analysis and gap_analysis.requires_enrichment:
            gap_penalty = min(0.2, gap_analysis.total_gaps * 0.05)
            adjusted = max(0.0, adjusted - gap_penalty)

        if source_count == 0:
            adjusted = 0.0
        elif source_count < 2:
            adjusted *= 0.9

        level = self._get_level(adjusted)

        return adjusted, level

    def _get_level(self, score: float) -> ConfidenceLevel:
        """Map score to confidence level."""
        if score >= self.thresholds.high:
            return ConfidenceLevel.HIGH
        elif score >= self.thresholds.medium:
            return ConfidenceLevel.MEDIUM
        elif score >= self.thresholds.low:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def requires_enrichment(self, level: ConfidenceLevel) -> bool:
        """Check if enrichment is needed based on confidence level."""
        return level in (ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW)


class ResponseBuilder:
    """Builds structured API responses."""

    def __init__(self):
        self._source_fields = [
            "path",
            "snippet",
            "relevance_score",
            "title",
            "last_modified",
            "authority_score",
        ]

    def build(
        self,
        response_text: str,
        sources: list[dict],
        confidence: float,
        confidence_level: ConfidenceLevel,
        gap_analysis: Optional[GapAnalysis] = None,
        enrichment_triggered: bool = False,
        request_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> QueryResponse:
        """Build complete QueryResponse."""

        formatted_sources = self._format_sources(sources)

        gaps = []
        if gap_analysis and gap_analysis.gaps:
            gaps = [
                {
                    "type": g.gap_type.value,
                    "topic": g.topic,
                    "priority": g.priority.name,
                    "description": g.description,
                }
                for g in gap_analysis.gaps
            ]

        return QueryResponse(
            ok=error is None,
            response=response_text,
            sources=formatted_sources,
            confidence=confidence,
            confidence_level=confidence_level.value,
            gaps_detected=gaps,
            enrichment_triggered=enrichment_triggered,
            request_id=request_id or str(uuid.uuid4()),
            error=error,
        )

    def _format_sources(self, sources: list[dict]) -> list[dict]:
        """Format sources to include only required fields."""
        formatted = []
        for source in sources:
            formatted_source = {}
            for field in self._source_fields:
                if field in source:
                    formatted_source[field] = source[field]
            if formatted_source:
                formatted.append(formatted_source)
        return formatted

    def build_error_response(
        self, error: str, request_id: Optional[str] = None
    ) -> QueryResponse:
        """Build error response."""
        return QueryResponse(
            ok=False,
            response="",
            sources=[],
            confidence=0.0,
            confidence_level=ConfidenceLevel.VERY_LOW.value,
            request_id=request_id or str(uuid.uuid4()),
            error=error,
        )


class QueryOrchestrator:
    """
    Main orchestrator for query processing.
    Coordinates: retrieval → confidence → synthesis → citation
    """

    def __init__(
        self,
        repository: Optional[KnowledgeRepository] = None,
        query_analyzer: Optional[QueryAnalyzer] = None,
        retrieval_orchestrator: Optional[RetrievalOrchestrator] = None,
        context_builder: Optional[ContextBuilder] = None,
        gap_detector: Optional[GapDetector] = None,
        confidence_thresholds: Optional[ConfidenceThreshold] = None,
        enable_enrichment: bool = True,
    ):
        self.repository = repository
        self.query_analyzer = query_analyzer or QueryAnalyzer()
        self.retrieval_orchestrator = retrieval_orchestrator
        self.context_builder = context_builder or ContextBuilder()
        self.gap_detector = gap_detector or GapDetector()

        self.confidence_assessor = ConfidenceAssessor(confidence_thresholds)
        self.response_builder = ResponseBuilder()

        self.enable_enrichment = enable_enrichment

    def process(
        self, query: str, synthesis_callback=None, enrichment_callback=None
    ) -> QueryResponse:
        """
        Process query through complete pipeline.

        Args:
            query: User query string
            synthesis_callback: Optional async function to synthesize response
            enrichment_callback: Optional async function for enrichment

        Returns:
            QueryResponse with all required fields
        """
        request_id = str(uuid.uuid4())

        try:
            parsed_query = self.query_analyzer.analyze(query)

            retrieval_context = None
            if self.retrieval_orchestrator and self.repository:
                retrieval_context = self.retrieval_orchestrator.retrieve(
                    parsed_query=parsed_query, repository=self.repository
                )

            context_window = None
            if retrieval_context:
                context_window = self.context_builder.build(
                    query=parsed_query, retrieval_context=retrieval_context
                )

            confidence, confidence_level = self.confidence_assessor.assess(
                confidence_score=retrieval_context.confidence
                if retrieval_context
                else 0.0,
                source_count=len(retrieval_context.results) if retrieval_context else 0,
            )

            gap_analysis = None
            if retrieval_context:
                gap_analysis = self.gap_detector.detect_gaps(
                    query=query,
                    confidence_score=confidence,
                    retrieved_sources=retrieval_context.results,
                    context_summary=context_window.system_prompt[:500]
                    if context_window
                    else "",
                )

            enrichment_triggered = False
            if (
                self.enable_enrichment
                and self.confidence_assessor.requires_enrichment(confidence_level)
                and enrichment_callback
            ):
                enrichment_result = enrichment_callback(
                    query=query,
                    confidence=confidence,
                    retrieval_context=retrieval_context,
                    gap_analysis=gap_analysis,
                )
                enrichment_triggered = enrichment_result.get(
                    "enrichment_triggered", False
                )

            response_text = ""
            if synthesis_callback and context_window:
                response_text = synthesis_callback(context_window, parsed_query)
            elif retrieval_context:
                response_text = self._default_synthesis(retrieval_context)

            sources = []
            if retrieval_context:
                sources = [
                    {
                        "path": res.get("path", ""),
                        "snippet": res.get("snippet", ""),
                        "relevance_score": res.get("score", 0.0),
                        "title": res.get("title", ""),
                        "last_modified": res.get("last_modified", ""),
                        "authority_score": res.get("authority_score", 0.5),
                    }
                    for res in retrieval_context.results[:10]
                ]

            return self.response_builder.build(
                response_text=response_text,
                sources=sources,
                confidence=confidence,
                confidence_level=confidence_level,
                gap_analysis=gap_analysis,
                enrichment_triggered=enrichment_triggered,
                request_id=request_id,
            )

        except Exception as e:
            return self.response_builder.build_error_response(
                error=str(e), request_id=request_id
            )

    def _default_synthesis(self, retrieval_context) -> str:
        """Default synthesis when no LLM callback provided."""
        if not retrieval_context.results:
            return "No relevant information found."

        top_result = retrieval_context.results[0]
        snippet = top_result.get("snippet", "")
        title = top_result.get("title", "")

        return f"Based on '{title}': {snippet[:500]}..."

    def set_repository(self, repository: KnowledgeRepository):
        """Set the knowledge repository."""
        self.repository = repository

    def set_retrieval_orchestrator(self, orchestrator: RetrievalOrchestrator):
        """Set the retrieval orchestrator."""
        self.retrieval_orchestrator = orchestrator
