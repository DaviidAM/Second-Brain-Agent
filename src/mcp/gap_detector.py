"""
Gap Detection Module - Phase 4: Write and Enrichment Pipeline
Identifies knowledge gaps from confidence scores and missing content signals.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import re


class GapType(Enum):
    """Types of knowledge gaps that can be detected."""
    MISSING_DEFINITION = "missing_definition"
    INCOMPLETE_COMPARISON = "incomplete_comparison"
    OUTDATED_INFO = "outdated_info"
    MISSING_EXAMPLE = "missing_example"
    UNKNOWN_TOPIC = "unknown_topic"
    PARTIAL_EXPLANATION = "partial_explanation"
    MISSING_PREREQUISITES = "missing_prerequisites"


class GapPriority(Enum):
    """Priority levels for gap resolution."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class KnowledgeGap:
    """Represents a detected knowledge gap."""
    gap_type: GapType
    topic: str
    description: str
    priority: GapPriority
    related_queries: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    source_documents: list[str] = field(default_factory=list)
    suggested_approach: Optional[str] = None

    def to_enrichment_prompt(self) -> str:
        """Generate a prompt for LLM enrichment."""
        prompt_parts = [
            f"Topic: {self.topic}",
            f"Gap Type: {self.gap_type.value}",
            f"Description: {self.description}",
        ]
        if self.suggested_approach:
            prompt_parts.append(f"Suggested Approach: {self.suggested_approach}")
        return "\n".join(prompt_parts)


@dataclass
class GapAnalysis:
    """Complete analysis of gaps in the knowledge base."""
    gaps: list[KnowledgeGap] = field(default_factory=list)
    total_gaps: int = 0
    critical_gaps: int = 0
    high_gaps: int = 0
    requires_enrichment: bool = False

    def get_prioritized_gaps(self) -> list[KnowledgeGap]:
        """Return gaps sorted by priority."""
        return sorted(self.gaps, key=lambda g: g.priority.value)


class GapClassifier:
    """Classifies detected gaps into types."""

    def __init__(self):
        self._type_patterns = {
            GapType.MISSING_DEFINITION: [
                r"what is\s+", r"define\s+", r"meaning of\s+",
                r"what does\s+", r"definition of\s+"
            ],
            GapType.INCOMPLETE_COMPARISON: [
                r"difference between\s+", r"compare\s+", r"vs\.?\s+",
                r"versus\s+", r"better than\s+", r"advantages?\s+.*disadvantages?"
            ],
            GapType.OUTDATED_INFO: [
                r"latest\s+", r"new version\s+", r"update\s+",
                r"recent\s+", r"current\s+"
            ],
            GapType.MISSING_EXAMPLE: [
                r"example\s+", r"how to\s+", r"sample\s+",
                r"use case\s+", r"implementation\s+"
            ],
            GapType.UNKNOWN_TOPIC: [
                r"how does\s+", r"why does\s+", r"explain\s+",
                r"describe\s+", r"what happens\s+"
            ],
        }

    def classify(self, query: str, context: str) -> GapType:
        """Classify a gap based on query and context."""
        query_lower = query.lower()
        
        for gap_type, patterns in self._type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return gap_type
        
        return GapType.PARTIAL_EXPLANATION


class GapPrioritizer:
    """Prioritizes gaps based on relevance and user intent."""

    def __init__(self):
        self._priority_boost_keywords = {
            "critical": ["urgent", "critical", "important", "asap"],
            "high": ["need", "must", "required", "essential"],
            "medium": ["should", "would like", "interested"],
            "low": ["could", "maybe", "sometime"],
        }

    def prioritize(
        self,
        gap: KnowledgeGap,
        query: str,
        confidence_score: float
    ) -> GapPriority:
        """Determine priority for a gap."""
        query_lower = query.lower()
        
        if confidence_score < 0.3:
            return GapPriority.CRITICAL
        
        for keyword in self._priority_boost_keywords["critical"]:
            if keyword in query_lower:
                return GapPriority.CRITICAL
        
        if confidence_score < 0.5:
            return GapPriority.HIGH
        
        for keyword in self._priority_boost_keywords["high"]:
            if keyword in query_lower:
                return GapPriority.HIGH
        
        if confidence_score < 0.7:
            return GapPriority.MEDIUM
        
        return GapPriority.LOW


class GapDetector:
    """
    Main gap detection class that identifies knowledge gaps
    from confidence scores and missing content signals.
    """

    def __init__(self):
        self.classifier = GapClassifier()
        self.prioritizer = GapPrioritizer()

    def detect_gaps(
        self,
        query: str,
        confidence_score: float,
        retrieved_sources: list[dict],
        context_summary: str
    ) -> GapAnalysis:
        """
        Detect knowledge gaps from retrieval results.
        
        Args:
            query: The original user query
            confidence_score: Confidence score from retrieval (0-1)
            retrieved_sources: List of source documents retrieved
            context_summary: Summary of the retrieved context
            
        Returns:
            GapAnalysis with detected gaps
        """
        gaps = []
        
        if confidence_score < 0.7:
            gap_type = self.classifier.classify(query, context_summary)
            
            gap = KnowledgeGap(
                gap_type=gap_type,
                topic=self._extract_topic(query),
                description=self._generate_description(
                    query, confidence_score, retrieved_sources
                ),
                priority=GapPriority.HIGH,
                related_queries=[query],
                confidence_score=confidence_score,
                source_documents=[
                    s.get("path", "") for s in retrieved_sources
                ],
                suggested_approach=self._suggest_approach(gap_type)
            )
            
            gap.priority = self.prioritizer.prioritize(
                gap, query, confidence_score
            )
            gaps.append(gap)
        
        if not retrieved_sources:
            gap = KnowledgeGap(
                gap_type=GapType.UNKNOWN_TOPIC,
                topic=self._extract_topic(query),
                description=f"No relevant sources found for query: {query}",
                priority=GapPriority.CRITICAL,
                related_queries=[query],
                confidence_score=0.0,
                source_documents=[],
                suggested_approach="Create new document with comprehensive information"
            )
            gaps.append(gap)
        
        return GapAnalysis(
            gaps=gaps,
            total_gaps=len(gaps),
            critical_gaps=sum(1 for g in gaps if g.priority == GapPriority.CRITICAL),
            high_gaps=sum(1 for g in gaps if g.priority == GapPriority.HIGH),
            requires_enrichment=len(gaps) > 0
        )

    def _extract_topic(self, query: str) -> str:
        """Extract main topic from query."""
        words = query.lower().split()
        stop_words = {"what", "how", "why", "when", "where", "is", "are", "the", "a", "an", "to", "for"}
        topic_words = [w for w in words if w not in stop_words and len(w) > 2]
        return " ".join(topic_words[:5]) if topic_words else query[:50]

    def _generate_description(
        self,
        query: str,
        confidence: float,
        sources: list[dict]
    ) -> str:
        """Generate a description of the gap."""
        if confidence == 0.0:
            return f"No information available for: {query}"
        elif confidence < 0.5:
            return f"Insufficient information to fully answer: {query}"
        elif confidence < 0.7:
            return f"Partial information available. Need more details for: {query}"
        else:
            return f"Additional context may enhance answer for: {query}"

    def _suggest_approach(self, gap_type: GapType) -> str:
        """Suggest approach for filling the gap."""
        suggestions = {
            GapType.MISSING_DEFINITION: "Provide clear definition with examples",
            GapType.INCOMPLETE_COMPARISON: "Add comparison table or detailed analysis",
            GapType.OUTDATED_INFO: "Research latest information and update content",
            GapType.MISSING_EXAMPLE: "Add practical examples and use cases",
            GapType.UNKNOWN_TOPIC: "Create comprehensive documentation",
            GapType.PARTIAL_EXPLANATION: "Expand existing content with more details",
            GapType.MISSING_PREREQUISITES: "Add prerequisite information and context",
        }
        return suggestions.get(gap_type, "Research and add relevant content")

    def generate_gap_summary(self, analysis: GapAnalysis) -> str:
        """Generate a summary of gaps for reporting."""
        if not analysis.gaps:
            return "No knowledge gaps detected."
        
        summary_parts = [
            f"Total gaps: {analysis.total_gaps}",
            f"Critical: {analysis.critical_gaps}",
            f"High: {analysis.high_gaps}",
            "",
            "Detected gaps:"
        ]
        
        for gap in analysis.get_prioritized_gaps():
            summary_parts.append(
                f"  - [{gap.priority.name}] {gap.gap_type.value}: {gap.topic}"
            )
        
        return "\n".join(summary_parts)
