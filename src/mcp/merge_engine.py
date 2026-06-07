"""
Merge Engine - Phase 4: Write and Enrichment Pipeline
Handles deduplication and merging of knowledge base content.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import hashlib
import re


class MergeStrategy(Enum):
    """Strategies for merging content."""
    APPEND = "append"
    REPLACE = "replace"
    PRESERVE = "preserve"
    HYBRID = "hybrid"


@dataclass
class MergeCandidate:
    """Represents content to be merged."""
    source_path: str
    content: str
    title: str
    similarity_score: float = 0.0
    merge_strategy: MergeStrategy = MergeStrategy.APPEND


@dataclass
class MergeResult:
    """Result of a merge operation."""
    success: bool
    merged_content: str
    strategy_used: MergeStrategy
    conflicts_resolved: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class DeduplicationResult:
    """Result of deduplication check."""
    is_duplicate: bool
    duplicate_of: Optional[str] = None
    similarity_score: float = 0.0
    duplicate_content: Optional[str] = None


class ContentDeduplicator:
    """Detects duplicate or near-duplicate content."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def check_duplicate(
        self,
        content: str,
        existing_contents: dict[str, str]
    ) -> DeduplicationResult:
        """
        Check if content is duplicate of existing content.
        
        Args:
            content: Content to check
            existing_contents: Dict of path -> content to compare against
            
        Returns:
            DeduplicationResult with findings
        """
        content_hash = self._normalize_hash(content)
        
        for path, existing in existing_contents.items():
            existing_hash = self._normalize_hash(existing)
            
            if content_hash == existing_hash:
                return DeduplicationResult(
                    is_duplicate=True,
                    duplicate_of=path,
                    similarity_score=1.0,
                    duplicate_content=existing
                )
            
            similarity = self._calculate_similarity(content, existing)
            if similarity >= self.similarity_threshold:
                return DeduplicationResult(
                    is_duplicate=True,
                    duplicate_of=path,
                    similarity_score=similarity,
                    duplicate_content=existing
                )
        
        return DeduplicationResult(is_duplicate=False, similarity_score=0.0)

    def _normalize_hash(self, content: str) -> str:
        """Create normalized hash for exact duplicate detection."""
        normalized = re.sub(r'\s+', ' ', content.lower().strip())
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity score between two content pieces."""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0

    def find_similar(
        self,
        content: str,
        existing_contents: dict[str, str],
        top_k: int = 5
    ) -> list[tuple[str, float]]:
        """
        Find most similar content pieces.
        
        Returns:
            List of (path, similarity_score) tuples
        """
        similarities = []
        
        for path, existing in existing_contents.items():
            similarity = self._calculate_similarity(content, existing)
            similarities.append((path, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


class ConflictResolver:
    """Resolves conflicts when merging overlapping content."""

    def __init__(self):
        self._conflict_markers = {
            "heading": r'^#{1,6}\s+',
            "code_block": r'^```',
            "list_item": r'^[\s]*[-*+]\s+',
            "definition": r'^.*:\s*$',
        }

    def detect_conflicts(
        self,
        existing: str,
        new: str
    ) -> list[dict]:
        """
        Detect conflicts between existing and new content.
        
        Returns:
            List of conflict dictionaries
        """
        conflicts = []
        
        existing_headings = self._extract_headings(existing)
        new_headings = self._extract_headings(new)
        
        common_headings = set(existing_headings) & set(new_headings)
        for heading in common_headings:
            conflicts.append({
                "type": "duplicate_heading",
                "heading": heading,
                "severity": "medium"
            })
        
        existing_code = self._extract_code_blocks(existing)
        new_code = self._extract_code_blocks(new)
        
        if existing_code and new_code:
            conflicts.append({
                "type": "code_conflict",
                "existing_blocks": len(existing_code),
                "new_blocks": len(new_code),
                "severity": "high"
            })
        
        return conflicts

    def resolve(
        self,
        existing: str,
        new: str,
        strategy: MergeStrategy
    ) -> MergeResult:
        """Resolve conflicts based on strategy."""
        conflicts = self.detect_conflicts(existing, new)
        
        if strategy == MergeStrategy.REPLACE:
            return MergeResult(
                success=True,
                merged_content=new,
                strategy_used=strategy,
                conflicts_resolved=[f"Replaced with new content ({len(conflicts)} conflicts)"]
            )
        
        if strategy == MergeStrategy.PRESERVE:
            return MergeResult(
                success=True,
                merged_content=existing,
                strategy_used=strategy,
                conflicts_resolved=["Preserved existing content"],
                warnings=[f"Ignored {len(conflicts)} conflicting sections"]
            )
        
        if strategy == MergeStrategy.APPEND:
            merged = self._merge_append(existing, new)
            return MergeResult(
                success=True,
                merged_content=merged,
                strategy_used=strategy,
                conflicts_resolved=[f"Appended new content ({len(conflicts)} conflicts)"]
            )
        
        merged = self._merge_hybrid(existing, new)
        return MergeResult(
            success=True,
            merged_content=merged,
            strategy_used=strategy,
            conflicts_resolved=[f"Hybrid merge ({len(conflicts)} conflicts)"]
        )

    def _extract_headings(self, content: str) -> list[str]:
        """Extract all headings from content."""
        pattern = r'^#{1,6}\s+(.+)$'
        return re.findall(pattern, content, re.MULTILINE)

    def _extract_code_blocks(self, content: str) -> list[str]:
        """Extract code blocks from content."""
        pattern = r'```[\s\S]*?```'
        return re.findall(pattern, content)

    def _merge_append(self, existing: str, new: str) -> str:
        """Merge by appending new content."""
        if not existing:
            return new
        
        separator = "\n\n---\n\n"
        return existing + separator + new

    def _merge_hybrid(self, existing: str, new: str) -> str:
        """Merge using hybrid strategy - update existing, append new."""
        existing_lines = existing.split('\n')
        new_lines = new.split('\n')
        
        result_lines = []
        new_headings = set(self._extract_headings(new))
        
        in_new_section = False
        for line in existing_lines:
            if re.match(r'^#{1,6}\s+', line):
                heading = re.sub(r'^#{1,6}\s+', '', line)
                in_new_section = heading in new_headings
            
            if not in_new_section:
                result_lines.append(line)
        
        result_lines.append("")
        result_lines.extend(new_lines)
        
        return '\n'.join(result_lines)


class MergeEngine:
    """
    Main merge engine for combining knowledge base content.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        default_strategy: MergeStrategy = MergeStrategy.APPEND
    ):
        self.deduplicator = ContentDeduplicator(similarity_threshold)
        self.conflict_resolver = ConflictResolver()
        self.default_strategy = default_strategy

    def merge(
        self,
        new_content: str,
        existing_content: Optional[str],
        strategy: Optional[MergeStrategy] = None,
        title: str = ""
    ) -> MergeResult:
        """
        Merge new content with existing content.
        
        Args:
            new_content: New content to merge
            existing_content: Existing content (if any)
            strategy: Merge strategy to use
            title: Title of the document
            
        Returns:
            MergeResult with merged content
        """
        if not existing_content:
            return MergeResult(
                success=True,
                merged_content=new_content,
                strategy_used=MergeStrategy.REPLACE,
                conflicts_resolved=["New document created"]
            )
        
        strategy = strategy or self.default_strategy
        
        return self.conflict_resolver.resolve(
            existing_content, new_content, strategy
        )

    def merge_with_deduplication(
        self,
        new_content: str,
        existing_contents: dict[str, str],
        strategy: Optional[MergeStrategy] = None,
        title: str = ""
    ) -> tuple[MergeResult, Optional[str]]:
        """
        Merge with deduplication check.
        
        Returns:
            Tuple of (MergeResult, duplicate_path or None)
        """
        dup_result = self.deduplicator.check_duplicate(new_content, existing_contents)
        
        if dup_result.is_duplicate and dup_result.similarity_score >= 0.95:
            return MergeResult(
                success=False,
                merged_content="",
                strategy_used=MergeStrategy.PRESERVE,
                error=f"Duplicate of {dup_result.duplicate_of}"
            ), dup_result.duplicate_of
        
        existing = existing_contents.get(title, "")
        
        merge_result = self.merge(new_content, existing, strategy, title)
        
        return merge_result, dup_result.duplicate_of

    def suggest_strategy(
        self,
        new_content: str,
        existing_content: str,
        query_context: str = ""
    ) -> MergeStrategy:
        """Suggest optimal merge strategy based on content analysis."""
        if not existing_content:
            return MergeStrategy.REPLACE
        
        conflicts = self.conflict_resolver.detect_conflicts(existing_content, new_content)
        
        high_severity = any(c.get("severity") == "high" for c in conflicts)
        if high_severity:
            return MergeStrategy.HYBRID
        
        if "update" in query_context.lower() or "latest" in query_context.lower():
            return MergeStrategy.REPLACE
        
        return MergeStrategy.APPEND
