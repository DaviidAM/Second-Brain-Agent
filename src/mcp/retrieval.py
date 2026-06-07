"""
Retrieval orchestration for hybrid search and cross-document aggregation.
Phase 3: Read Pipeline - Retrieval Orchestration
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time

from .query_analyzer import ParsedQuery, QueryComplexity
from .indexing import SearchResult


class RetrievalMode(str, Enum):
    """Retrieval strategy modes."""
    KEYWORD_ONLY = "keyword"
    VECTOR_ONLY = "vector"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"  # Choose based on query type


@dataclass
class RetrievalContext:
    """Context for a retrieval operation."""
    query: ParsedQuery
    mode: RetrievalMode
    max_results: int = 5
    max_context_tokens: int = 3000
    include_related: bool = True
    cross_document_depth: int = 2
    time_decay_enabled: bool = True
    authority_boost: bool = True
    
    execution_time_ms: float = 0.0
    results_count: int = 0


@dataclass
class AggregatedResult:
    """Aggregated result from multiple documents."""
    primary_filepath: str
    primary_title: str
    primary_snippet: str
    primary_score: float
    
    related_docs: List[Dict[str, Any]] = field(default_factory=list)
    combined_snippet: str = ""
    aggregated_score: float = 0.0
    context_tokens_used: int = 0
    sources: List[str] = field(default_factory=list)


class HybridRetriever:
    """Orchestrates hybrid keyword + vector retrieval."""
    
    @staticmethod
    def retrieve(
        parsed_query: ParsedQuery,
        keyword_results: List[SearchResult],
        vector_results: Optional[List[SearchResult]] = None,
        mode: RetrievalMode = RetrievalMode.HYBRID,
    ) -> List[SearchResult]:
        """
        Combine keyword and vector results using hybrid ranking.
        
        Args:
            parsed_query: Analyzed query
            keyword_results: Results from keyword search
            vector_results: Results from vector search (optional)
            mode: Retrieval mode
            
        Returns:
            Ranked list of SearchResult objects
        """
        start_time = time.time()
        
        if mode == RetrievalMode.KEYWORD_ONLY or vector_results is None:
            return keyword_results
        
        if mode == RetrievalMode.VECTOR_ONLY:
            return vector_results
        
        # Hybrid mode: combine and re-rank
        combined = HybridRetriever._combine_results(keyword_results, vector_results)
        ranked = HybridRetriever._reciprocal_rank_fusion(combined)
        
        return ranked[:10]  # Return top 10
    
    @staticmethod
    def _combine_results(
        keyword_results: List[SearchResult],
        vector_results: List[SearchResult]
    ) -> Dict[str, Tuple[SearchResult, float]]:
        """
        Combine results from both retrieval methods.
        
        Returns:
            Dict mapping filepath -> (SearchResult, combined_score)
        """
        combined = {}
        
        # Add keyword results
        for i, result in enumerate(keyword_results):
            score = (len(keyword_results) - i) / len(keyword_results)
            combined[result.filepath] = (result, score)
        
        # Add/merge vector results
        for i, result in enumerate(vector_results):
            vector_score = (len(vector_results) - i) / len(vector_results)
            if result.filepath in combined:
                # Merge scores
                existing_result, existing_score = combined[result.filepath]
                combined[result.filepath] = (existing_result, (existing_score + vector_score) / 2)
            else:
                combined[result.filepath] = (result, vector_score)
        
        return combined
    
    @staticmethod
    def _reciprocal_rank_fusion(
        combined: Dict[str, Tuple[SearchResult, float]]
    ) -> List[SearchResult]:
        """
        Apply Reciprocal Rank Fusion to combine rankings.
        
        Formula: RRF(d) = Σ(1 / (k + rank(d)))
        """
        k = 60  # Constant
        rrf_scores = {}
        
        for filepath, (result, score) in combined.items():
            rank = int(1 / max(score, 0.01))  # Inverse score to rank
            rrf_score = 1 / (k + rank)
            rrf_scores[filepath] = (result, rrf_score)
        
        # Sort by RRF score
        sorted_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1][1],
            reverse=True
        )
        
        return [result for _, (result, _) in sorted_results]


class CrossDocumentAggregator:
    """Aggregates information across multiple related documents."""
    
    @staticmethod
    def aggregate(
        primary_result: SearchResult,
        related_results: List[SearchResult],
        max_tokens: int = 3000,
        query_complexity: QueryComplexity = QueryComplexity.MODERATE,
    ) -> AggregatedResult:
        """
        Aggregate primary result with related documents.
        
        Args:
            primary_result: Main search result
            related_results: Related documents to include
            max_tokens: Maximum tokens for aggregated context
            query_complexity: Query complexity level
            
        Returns:
            AggregatedResult with combined context
        """
        aggregated = AggregatedResult(
            primary_filepath=primary_result.filepath,
            primary_title=primary_result.title,
            primary_snippet=primary_result.snippet,
            primary_score=primary_result.relevance_score,
        )
        
        # Add sources
        aggregated.sources.append(primary_result.filepath)
        
        # Allocate tokens
        tokens_used = CrossDocumentAggregator._estimate_tokens(primary_result.snippet)
        aggregated.context_tokens_used = tokens_used
        
        # Include related documents based on complexity
        if query_complexity == QueryComplexity.SIMPLE:
            related_to_include = related_results[:1]
        elif query_complexity == QueryComplexity.MODERATE:
            related_to_include = related_results[:2]
        else:
            related_to_include = related_results[:4]
        
        for related in related_to_include:
            related_tokens = CrossDocumentAggregator._estimate_tokens(related.snippet)
            
            if aggregated.context_tokens_used + related_tokens > max_tokens * 0.8:
                break  # Stop if approaching token limit
            
            aggregated.related_docs.append({
                "filepath": related.filepath,
                "title": related.title,
                "snippet": related.snippet,
                "relevance_score": related.relevance_score,
            })
            
            aggregated.sources.append(related.filepath)
            aggregated.context_tokens_used += related_tokens
        
        # Build combined snippet
        aggregated.combined_snippet = CrossDocumentAggregator._build_combined_snippet(
            aggregated
        )
        
        # Calculate aggregated score
        aggregated.aggregated_score = CrossDocumentAggregator._calculate_aggregated_score(
            aggregated
        )
        
        return aggregated
    
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimation (1 token ~= 4 chars)."""
        return len(text) // 4
    
    @staticmethod
    def _build_combined_snippet(aggregated: AggregatedResult) -> str:
        """Build combined snippet from primary and related docs."""
        lines = [
            f"# {aggregated.primary_title}",
            f"\n{aggregated.primary_snippet}\n",
        ]
        
        for related in aggregated.related_docs:
            lines.append(f"## Related: {related['title']}")
            lines.append(f"{related['snippet']}\n")
        
        return "\n".join(lines)
    
    @staticmethod
    def _calculate_aggregated_score(aggregated: AggregatedResult) -> float:
        """Calculate combined relevance score."""
        base_score = aggregated.primary_score
        
        # Boost for related documents
        related_boost = 0.0
        for related in aggregated.related_docs:
            related_boost += related["relevance_score"] * 0.1
        
        return min(base_score + related_boost, 1.0)


class ScoreNormalizer:
    """Normalizes scores across different retrieval methods."""
    
    @staticmethod
    def normalize_keyword_score(score: float) -> float:
        """
        Normalize keyword score to 0-1 range.
        
        Keyword scores typically range 1-50+ depending on matches.
        """
        # Apply sigmoid-like normalization
        normalized = score / (score + 10)
        return min(max(normalized, 0.0), 1.0)
    
    @staticmethod
    def normalize_vector_score(score: float) -> float:
        """
        Normalize vector score (cosine similarity) to 0-1 range.
        
        Vector scores typically range 0-1 already.
        """
        return min(max(score, 0.0), 1.0)
    
    @staticmethod
    def apply_time_decay(score: float, days_old: int, decay_rate: float = 0.05) -> float:
        """
        Apply time decay to older documents.
        
        Args:
            score: Original score
            days_old: Days since last modification
            decay_rate: Decay rate per day
            
        Returns:
            Decayed score
        """
        decay_factor = (1 - decay_rate) ** days_old
        return score * decay_factor
    
    @staticmethod
    def apply_authority_boost(
        score: float,
        authority_score: float,
        source_type: str,
    ) -> float:
        """
        Apply authority boost based on document quality.
        
        Args:
            score: Original score
            authority_score: Document authority (0-1)
            source_type: "manual" or "llm-generated"
            
        Returns:
            Boosted score
        """
        # Manual documents get higher authority boost
        if source_type == "manual":
            boost = authority_score * 0.2
        else:
            boost = authority_score * 0.1
        
        return min(score + boost, 1.0)
    
    @staticmethod
    def normalize_results(
        results: List[SearchResult],
        time_decay_enabled: bool = False,
        authority_boost_enabled: bool = False,
    ) -> List[SearchResult]:
        """
        Normalize and boost all results.
        
        Args:
            results: List of search results
            time_decay_enabled: Apply time decay to older docs
            authority_boost_enabled: Apply authority boost
            
        Returns:
            Normalized results
        """
        for result in results:
            # Normalize to 0-1 range
            result.relevance_score = ScoreNormalizer.normalize_keyword_score(result.relevance_score)
            
            # Apply time decay if enabled
            if time_decay_enabled and result.last_modified:
                # Calculate days old (simplified)
                days_old = 0  # Would calculate from last_modified
                result.relevance_score = ScoreNormalizer.apply_time_decay(
                    result.relevance_score,
                    days_old
                )
            
            # Apply authority boost if enabled
            if authority_boost_enabled:
                result.relevance_score = ScoreNormalizer.apply_authority_boost(
                    result.relevance_score,
                    result.relevance_score,  # Use relevance as proxy
                    "manual"  # Would use actual source_type
                )
        
        # Re-sort by normalized score
        return sorted(results, key=lambda r: r.relevance_score, reverse=True)


class RetrievalOrchestrator:
    """Main orchestrator for the entire retrieval pipeline."""
    
    def __init__(self, keyword_index: Dict, vector_index: Optional[Dict] = None):
        """
        Initialize orchestrator.
        
        Args:
            keyword_index: Keyword search index
            vector_index: Optional vector index
        """
        self.keyword_index = keyword_index
        self.vector_index = vector_index
    
    def retrieve(
        self,
        parsed_query: ParsedQuery,
        keyword_results: List[SearchResult],
        vector_results: Optional[List[SearchResult]] = None,
        context: Optional[RetrievalContext] = None,
    ) -> List[AggregatedResult]:
        """
        Execute full retrieval pipeline.
        
        Args:
            parsed_query: Analyzed query
            keyword_results: Results from keyword search
            vector_results: Optional results from vector search
            context: Retrieval context
            
        Returns:
            List of aggregated results
        """
        if context is None:
            context = RetrievalContext(
                query=parsed_query,
                mode=RetrievalMode.HYBRID,
            )
        
        start_time = time.time()
        
        # Step 1: Hybrid ranking
        hybrid_results = HybridRetriever.retrieve(
            parsed_query,
            keyword_results,
            vector_results,
            context.mode,
        )
        
        # Step 2: Normalize scores
        normalized_results = ScoreNormalizer.normalize_results(
            hybrid_results,
            context.time_decay_enabled,
            context.authority_boost,
        )
        
        # Step 3: Aggregate with related documents
        aggregated = []
        for i, primary_result in enumerate(normalized_results[:context.max_results]):
            # Find related documents
            related = self._find_related_documents(
                primary_result,
                normalized_results,
                depth=context.cross_document_depth,
            )
            
            # Aggregate
            agg_result = CrossDocumentAggregator.aggregate(
                primary_result,
                related,
                context.max_context_tokens,
                parsed_query.complexity,
            )
            
            aggregated.append(agg_result)
        
        context.execution_time_ms = (time.time() - start_time) * 1000
        context.results_count = len(aggregated)
        
        return aggregated
    
    def _find_related_documents(
        self,
        primary: SearchResult,
        all_results: List[SearchResult],
        depth: int = 2,
    ) -> List[SearchResult]:
        """Find documents related to primary result."""
        # For now, return next N results
        # In Phase 5, use wikilink graph for better relationships
        idx = all_results.index(primary)
        return all_results[idx+1:idx+depth+1]
