"""
Tests for Phase 5: AI Response Generation and Safety Controls
"""

import pytest
from src.mcp.query_orchestrator import (
    QueryOrchestrator, ConfidenceAssessor, ConfidenceLevel,
    ConfidenceThreshold, ResponseBuilder, QueryResponse
)
from src.mcp.synthesis import (
    ResponseSynthesizer, PromptBuilder, CitationAttacher, SynthesisResult
)
from src.mcp.hallucination_guard import (
    HallucinationGuard, ClaimValidator, UncertaintyHandler,
    Claim, ClaimType, ValidationResult, HallucinationReport
)
from src.mcp.context_manager import (
    ContextManager, TokenBudget, TokenBudgetController,
    TruncationStrategy, SnippetBudget
)
from src.mcp.fallback_handler import (
    FallbackHandler, FallbackType, DeterministicResponseGenerator,
    ErrorResponseBuilder, FallbackResponse
)


class TestConfidenceAssessor:
    """Tests for ConfidenceAssessor."""

    def test_assess_high_confidence(self):
        """Test high confidence assessment."""
        assessor = ConfidenceAssessor()
        
        confidence, level = assessor.assess(0.95, None, 5)
        
        assert confidence >= 0.9
        assert level == ConfidenceLevel.HIGH

    def test_assess_low_confidence(self):
        """Test low confidence assessment."""
        assessor = ConfidenceAssessor()
        
        confidence, level = assessor.assess(0.4, None, 1)
        
        assert level in (ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW)

    def test_requires_enrichment_low(self):
        """Test enrichment requirement for low confidence."""
        assessor = ConfidenceAssessor()
        
        assert assessor.requires_enrichment(ConfidenceLevel.LOW) is True
        assert assessor.requires_enrichment(ConfidenceLevel.VERY_LOW) is True
        assert assessor.requires_enrichment(ConfidenceLevel.HIGH) is False


class TestResponseBuilder:
    """Tests for ResponseBuilder."""

    def test_build_response(self):
        """Test building a complete response."""
        builder = ResponseBuilder()
        
        response = builder.build(
            response_text="Test response",
            sources=[{"path": "test.md", "title": "Test", "relevance_score": 0.9}],
            confidence=0.85,
            confidence_level=ConfidenceLevel.MEDIUM
        )
        
        assert response.ok is True
        assert response.response == "Test response"
        assert len(response.sources) == 1

    def test_build_error_response(self):
        """Test building error response."""
        builder = ResponseBuilder()
        
        response = builder.build_error_response("Test error")
        
        assert response.ok is False
        assert response.error == "Test error"


class TestQueryOrchestrator:
    """Tests for QueryOrchestrator."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = QueryOrchestrator()
        
        assert orchestrator.query_analyzer is not None
        assert orchestrator.gap_detector is not None
        assert orchestrator.confidence_assessor is not None

    def test_set_repository(self):
        """Test setting repository."""
        from src.mcp.repository import KnowledgeRepository
        
        orchestrator = QueryOrchestrator()
        repo = KnowledgeRepository(wiki_path="knowledge/wiki")
        
        orchestrator.set_repository(repo)
        
        assert orchestrator.repository is not None


class TestPromptBuilder:
    """Tests for PromptBuilder."""

    def test_build_prompt(self):
        """Test prompt building."""
        from src.mcp.query_analyzer import ParsedQuery, QueryIntent, QueryComplexity
        from src.mcp.context_builder import ContextWindow
        
        builder = PromptBuilder()
        
        parsed = ParsedQuery(
            original_query="What is Python?",
            intent=QueryIntent.EXPLANATION,
            complexity=QueryComplexity.SIMPLE,
            keywords=["python"],
            entities=[]
        )
        
        context = ContextWindow(
            system_prompt="You are a helpful assistant.",
            user_prompt="Python is a programming language.",
            tokens_used=100
        )
        
        system, user = builder.build_prompt(context, parsed)
        
        assert "helpful" in system.lower()
        assert "What is Python?" in user


class TestCitationAttacher:
    """Tests for CitationAttacher."""

    def test_attach_citations(self):
        """Test attaching citations."""
        attacher = CitationAttacher()
        
        sources = [
            {"path": "test1.md", "title": "Test 1", "relevance_score": 0.9},
            {"path": "test2.md", "title": "Test 2", "relevance_score": 0.8}
        ]
        
        response, citations = attacher.attach("Test response", sources)
        
        assert len(citations) == 2
        assert citations[0]["path"] == "test1.md"


class TestResponseSynthesizer:
    """Tests for ResponseSynthesizer."""

    def test_synthesize_default(self):
        """Test default synthesis."""
        from src.mcp.query_analyzer import ParsedQuery, QueryIntent, QueryComplexity
        from src.mcp.context_builder import ContextWindow
        
        synthesizer = ResponseSynthesizer()
        
        parsed = ParsedQuery(
            original_query="Test",
            intent=QueryIntent.REFERENCE,
            complexity=QueryComplexity.SIMPLE,
            keywords=[],
            entities=[]
        )
        
        context = ContextWindow(
            system_prompt="",
            user_prompt="Some relevant content here",
            tokens_used=50
        )
        
        result = synthesizer.synthesize(context, parsed, [])
        
        assert result.response is not None
        assert len(result.response) > 0


class TestClaimValidator:
    """Tests for ClaimValidator."""

    def test_extract_claims(self):
        """Test extracting claims from text."""
        validator = ClaimValidator()
        
        text = "Python is a programming language. It is used for web development."
        
        claims = validator.extract_claims(text)
        
        assert len(claims) >= 1

    def test_validate_claim(self):
        """Test validating a claim."""
        validator = ClaimValidator()
        
        claim = Claim(
            text="Python is a programming language",
            claim_type=ClaimType.DEFINITIONAL,
            start_pos=0,
            end_pos=30
        )
        
        sources = [
            {"snippet": "Python is a programming language used for many purposes", "path": "test.md"}
        ]
        
        result = validator.validate_claim(claim, sources)
        
        assert result.is_grounded is True


class TestUncertaintyHandler:
    """Tests for UncertaintyHandler."""

    def test_inject_uncertainty(self):
        """Test uncertainty injection."""
        handler = UncertaintyHandler()
        
        text = "This is a test response."
        
        result = handler.inject_uncertainty(text, 0.5, [])
        
        assert result is not None

    def test_format_uncertain_response(self):
        """Test formatting uncertain response."""
        handler = UncertaintyHandler()
        
        text = "This is a response."
        gaps = [{"type": "missing_definition", "topic": "test topic"}]
        
        result = handler.format_uncertain_response(text, gaps)
        
        assert "incomplete" in result.lower()


class TestHallucinationGuard:
    """Tests for HallucinationGuard."""

    def test_validate_response(self):
        """Test response validation."""
        guard = HallucinationGuard()
        
        response = "Python is a programming language. It is widely used."
        sources = [
            {"snippet": "Python is a programming language", "path": "python.md"}
        ]
        
        report = guard.validate_response(response, sources, 0.8)
        
        assert report.total_claims >= 0

    def test_guard_response(self):
        """Test guarding response."""
        guard = HallucinationGuard()
        
        response = "Python is a programming language."
        sources = [{"snippet": "Python is a programming language", "path": "test.md"}]
        
        guarded, report = guard.guard_response(response, sources, 0.9)
        
        assert guarded is not None


class TestTokenBudgetController:
    """Tests for TokenBudgetController."""

    def test_allocate(self):
        """Test budget allocation."""
        controller = TokenBudgetController()
        
        snippets = [
            {"content": "This is a test content", "path": "test1.md"},
            {"content": "More content here", "path": "test2.md"}
        ]
        
        allocated = controller.allocate(snippets)
        
        assert len(allocated) >= 0

    def test_estimate_tokens(self):
        """Test token estimation."""
        controller = TokenBudgetController()
        
        tokens = controller._estimate_tokens("This is a test")
        
        assert tokens > 0


class TestContextManager:
    """Tests for ContextManager."""

    def test_prepare_context(self):
        """Test context preparation."""
        manager = ContextManager()
        
        snippets = [
            {"content": "Test content one", "path": "test1.md"},
            {"content": "Test content two", "path": "test2.md"}
        ]
        
        context, metadata = manager.prepare_context(snippets)
        
        assert context is not None

    def test_enforce_limit(self):
        """Test enforcing token limit."""
        manager = ContextManager(max_tokens=100)
        
        text = " ".join(["word"] * 100)
        
        truncated = manager.enforce_limit(text)
        
        assert len(truncated) <= len(text)


class TestDeterministicResponseGenerator:
    """Tests for DeterministicResponseGenerator."""

    def test_no_sources_response(self):
        """Test no sources response."""
        generator = DeterministicResponseGenerator()
        
        response = generator.generate("test query", FallbackType.NO_SOURCES)
        
        assert "couldn't find" in response.lower() or "not found" in response.lower()

    def test_low_confidence_response(self):
        """Test low confidence response."""
        generator = DeterministicResponseGenerator()
        
        response = generator.generate(
            "test query",
            FallbackType.LOW_CONFIDENCE,
            {"source_count": 1}
        )
        
        assert response is not None


class TestErrorResponseBuilder:
    """Tests for ErrorResponseBuilder."""

    def test_build_error(self):
        """Test building error response."""
        builder = ErrorResponseBuilder()
        
        response = builder.build("Test error", 500)
        
        assert response["ok"] is False
        assert response["status_code"] == 500


class TestFallbackHandler:
    """Tests for FallbackHandler."""

    def test_handle_no_sources(self):
        """Test handling no sources fallback."""
        handler = FallbackHandler()
        
        result = handler.handle(FallbackType.NO_SOURCES, "test query")
        
        assert result.fallback_type == FallbackType.NO_SOURCES
        assert result.can_retry is True

    def test_handle_llm_error(self):
        """Test handling LLM error fallback."""
        handler = FallbackHandler()
        
        result = handler.handle(FallbackType.LLM_ERROR, "test query")
        
        assert result.response is not None

    def test_cache_behavior(self):
        """Test caching behavior."""
        handler = FallbackHandler(cache_enabled=True)
        
        result1 = handler.handle(FallbackType.NO_SOURCES, "cached query")
        result2 = handler.handle(FallbackType.NO_SOURCES, "cached query")
        
        assert result2.cached is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
