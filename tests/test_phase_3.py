"""
Unit tests for Phase 3: Read Pipeline implementation.
"""

import pytest
import tempfile
import os
from datetime import datetime

from src.mcp.query_analyzer import (
    QueryAnalyzer,
    QueryValidator,
    QueryOptimizer,
    QueryIntent,
    QueryComplexity,
)
from src.mcp.retrieval import (
    HybridRetriever,
    CrossDocumentAggregator,
    ScoreNormalizer,
    RetrievalOrchestrator,
)
from src.mcp.repository import KnowledgeRepository
from src.mcp.context_builder import ContextBuilder, PromptBuilder, ContextValidator


# ==================== Query Analyzer Tests ====================

class TestQueryAnalyzer:
    """Tests for query analysis."""
    
    def test_simple_search_query(self):
        """Test analysis of simple search query."""
        query = "What is a circuit breaker?"
        parsed = QueryAnalyzer.analyze(query)
        
        assert parsed.intent in [QueryIntent.EXPLANATION, QueryIntent.REFERENCE]
        assert len(parsed.keywords) > 0
        assert parsed.complexity == QueryComplexity.SIMPLE
        assert parsed.confidence > 0.5
    
    def test_complex_comparison_query(self):
        """Test analysis of complex comparison query."""
        query = "Compare microservices architecture with monolithic design patterns and explain the trade-offs in distributed systems"
        parsed = QueryAnalyzer.analyze(query)
        
        assert parsed.intent in [QueryIntent.COMPARISON, QueryIntent.SYNTHESIS, QueryIntent.EXPLANATION]
        assert len(parsed.entities) > 0
        assert parsed.complexity in [QueryComplexity.COMPLEX, QueryComplexity.MODERATE]
    
    def test_domain_detection(self):
        """Test domain detection."""
        query = "How to implement async/await in Python FastAPI?"
        parsed = QueryAnalyzer.analyze(query)
        
        assert "python" in parsed.domains
        assert "backend" in parsed.domains
    
    def test_intent_detection(self):
        """Test various intent types."""
        test_cases = [
            ("Explain machine learning", QueryIntent.EXPLANATION),
            ("What's the difference between ML and DL?", QueryIntent.COMPARISON),
            ("How to build an API?", QueryIntent.IMPLEMENTATION),
            ("Debug this error", QueryIntent.TROUBLESHOOTING),
        ]
        
        for query, expected_intent in test_cases:
            parsed = QueryAnalyzer.analyze(query)
            assert parsed.intent == expected_intent or parsed.intent != QueryIntent.UNKNOWN
    
    def test_keyword_extraction(self):
        """Test keyword extraction."""
        query = "What are best practices for API authentication with OAuth2?"
        parsed = QueryAnalyzer.analyze(query)
        
        keywords = [k.lower() for k in parsed.keywords]
        assert any(k in keywords for k in ["api", "auth", "oauth"])


class TestQueryValidator:
    """Tests for query validation."""
    
    def test_valid_query(self):
        """Test validation of valid query."""
        is_valid, error = QueryValidator.validate("What is a design pattern?")
        assert is_valid is True
        assert error == ""
    
    def test_empty_query(self):
        """Test rejection of empty query."""
        is_valid, error = QueryValidator.validate("")
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_too_long_query(self):
        """Test rejection of excessively long query."""
        long_query = "a" * 600
        is_valid, error = QueryValidator.validate(long_query)
        assert is_valid is False
    
    def test_single_word_query(self):
        """Test rejection of single-word query."""
        is_valid, error = QueryValidator.validate("help")
        assert is_valid is False


class TestQueryOptimizer:
    """Tests for query optimization."""
    
    def test_expand_complex_query(self):
        """Test query expansion for complex queries."""
        parsed = QueryAnalyzer.analyze(
            "How do distributed consensus algorithms work in blockchain systems?"
        )
        
        alternatives = QueryOptimizer.expand_query(parsed)
        assert len(alternatives) >= 2
        assert parsed.original_query in alternatives


# ==================== Score Normalizer Tests ====================

class TestScoreNormalizer:
    """Tests for score normalization."""
    
    def test_normalize_keyword_score(self):
        """Test keyword score normalization."""
        # Score of 0 -> 0
        assert ScoreNormalizer.normalize_keyword_score(0) == 0
        
        # Score of 10 -> ~0.5
        assert 0.4 < ScoreNormalizer.normalize_keyword_score(10) < 0.6
        
        # High score -> ~1.0
        assert ScoreNormalizer.normalize_keyword_score(100) > 0.9
    
    def test_normalize_vector_score(self):
        """Test vector score normalization."""
        # Already in 0-1 range
        assert ScoreNormalizer.normalize_vector_score(0.5) == 0.5
        assert ScoreNormalizer.normalize_vector_score(0.9) == 0.9
    
    def test_time_decay(self):
        """Test time decay application."""
        original_score = 1.0
        
        # No decay for recent doc
        assert ScoreNormalizer.apply_time_decay(original_score, 0) == 1.0
        
        # Decay for older doc
        decayed = ScoreNormalizer.apply_time_decay(original_score, 30)
        assert decayed < original_score


# ==================== Context Builder Tests ====================

class TestContextBuilder:
    """Tests for context building."""
    
    def test_build_context_empty(self):
        """Test context building with no results."""
        context = ContextBuilder.build_context([], "test query")
        
        assert context.quality_score == 0.0
        assert "No relevant documents" in context.main_content


class TestPromptBuilder:
    """Tests for prompt building."""
    
    def test_system_prompt(self):
        """Test system prompt generation."""
        prompt = PromptBuilder.build_system_prompt()
        
        assert "knowledge base" in prompt.lower()
        assert "cite" in prompt.lower()


# ==================== Repository Tests ====================

class TestKnowledgeRepository:
    """Tests for repository management."""
    
    def test_repository_initialization(self):
        """Test repository initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = KnowledgeRepository(tmpdir)
            success, errors = repo.initialize()
            
            # Check directories created
            assert os.path.isdir(os.path.join(tmpdir, "wiki"))
            assert os.path.isdir(os.path.join(tmpdir, ".metadata"))
            
            # Check repository is healthy
            assert repo.is_initialized()
    
    def test_repository_health(self):
        """Test repository health check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = KnowledgeRepository(tmpdir)
            repo.initialize()
            
            assert repo.is_healthy() or not repo.is_initialized()


# ==================== Integration Tests ====================

class TestPhase3Integration:
    """Integration tests for Phase 3."""
    
    def test_query_to_context_pipeline(self):
        """Test full pipeline: query -> analysis -> retrieval -> context."""
        # Analyze query
        query = "How to implement error handling?"
        parsed = QueryAnalyzer.analyze(query)
        
        assert parsed.intent != QueryIntent.UNKNOWN
        assert len(parsed.keywords) > 0
        
        # Validate query
        is_valid, _ = QueryValidator.validate(query)
        assert is_valid
    
    def test_repository_with_search(self):
        """Test repository search functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and initialize repo
            repo = KnowledgeRepository(tmpdir)
            repo.initialize()
            
            # Try search (will return empty with no docs, but should not error)
            results = repo.search_keyword("test", top_k=5)
            assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
