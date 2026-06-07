"""
Tests for Phase 4: Write and Enrichment Pipeline
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.mcp.gap_detector import (
    GapDetector, GapType, GapPriority, KnowledgeGap, GapAnalysis,
    GapClassifier, GapPrioritizer
)
from src.mcp.enrichment_client import (
    EnrichmentClient, PromptTemplateManager, ResponseValidator,
    EnrichmentRequest, ValidationResult
)
from src.mcp.merge_engine import (
    MergeEngine, MergeStrategy, ContentDeduplicator, ConflictResolver,
    MergeResult, DeduplicationResult
)
from src.mcp.write_manager import (
    WriteManager, WriteOperation, WriteMode, TransactionLogger,
    RollbackHandler, WriteResult
)
from src.mcp.enrichment_orchestrator import (
    EnrichmentOrchestrator, EnrichmentContext, EnrichmentState,
    EnrichmentStatus, EnrichmentResult
)


class TestGapDetector:
    """Tests for GapDetector class."""

    def test_detect_gaps_low_confidence(self):
        """Test gap detection with low confidence score."""
        detector = GapDetector()
        
        result = detector.detect_gaps(
            query="What is machine learning?",
            confidence_score=0.4,
            retrieved_sources=[{"path": "ai/ml.md", "content": "ML is..."}],
            context_summary="Some context about ML"
        )
        
        assert result.requires_enrichment is True
        assert result.total_gaps >= 1
        assert result.critical_gaps + result.high_gaps >= 1

    def test_detect_gaps_no_sources(self):
        """Test gap detection with no sources."""
        detector = GapDetector()
        
        result = detector.detect_gaps(
            query="What is quantum computing?",
            confidence_score=0.0,
            retrieved_sources=[],
            context_summary=""
        )
        
        assert result.requires_enrichment is True
        assert result.critical_gaps >= 1

    def test_detect_gaps_high_confidence(self):
        """Test gap detection with high confidence (no gaps)."""
        detector = GapDetector()
        
        result = detector.detect_gaps(
            query="What is Python?",
            confidence_score=0.9,
            retrieved_sources=[{"path": "programming/python.md", "content": "Python is..."}],
            context_summary="Python is a programming language"
        )
        
        assert result.requires_enrichment is False
        assert result.total_gaps == 0

    def test_extract_topic(self):
        """Test topic extraction from query."""
        detector = GapDetector()
        
        topic = detector._extract_topic("What is the definition of machine learning?")
        assert "machine" in topic
        assert "learning" in topic
        assert "what" not in topic

    def test_generate_gap_summary(self):
        """Test gap summary generation."""
        detector = GapDetector()
        
        gap = KnowledgeGap(
            gap_type=GapType.MISSING_DEFINITION,
            topic="test topic",
            description="test description",
            priority=GapPriority.HIGH,
            confidence_score=0.4
        )
        
        analysis = GapAnalysis(
            gaps=[gap],
            total_gaps=1,
            critical_gaps=0,
            high_gaps=1,
            requires_enrichment=True
        )
        
        summary = detector.generate_gap_summary(analysis)
        assert "Total gaps: 1" in summary
        assert "HIGH" in summary


class TestGapClassifier:
    """Tests for GapClassifier."""

    def test_classify_definition(self):
        """Test classification of definition queries."""
        classifier = GapClassifier()
        
        gap_type = classifier.classify(
            "What is machine learning?",
            "No definition found"
        )
        
        assert gap_type == GapType.MISSING_DEFINITION

    def test_classify_comparison(self):
        """Test classification of comparison queries."""
        classifier = GapClassifier()
        
        gap_type = classifier.classify(
            "Difference between SQL and NoSQL",
            "No comparison found"
        )
        
        assert gap_type == GapType.INCOMPLETE_COMPARISON

    def test_classify_example(self):
        """Test classification of example queries."""
        classifier = GapClassifier()
        
        gap_type = classifier.classify(
            "How to implement authentication?",
            "No example found"
        )
        
        assert gap_type == GapType.MISSING_EXAMPLE


class TestGapPrioritizer:
    """Tests for GapPrioritizer."""

    def test_prioritize_critical_confidence(self):
        """Test critical priority for very low confidence."""
        prioritizer = GapPrioritizer()
        
        gap = KnowledgeGap(
            gap_type=GapType.UNKNOWN_TOPIC,
            topic="test",
            description="test",
            priority=GapPriority.LOW,
            confidence_score=0.2
        )
        
        priority = prioritizer.prioritize(gap, "test query", 0.2)
        
        assert priority == GapPriority.CRITICAL

    def test_prioritize_urgent_keyword(self):
        """Test priority boost for urgent keywords."""
        prioritizer = GapPrioritizer()
        
        gap = KnowledgeGap(
            gap_type=GapType.PARTIAL_EXPLANATION,
            topic="test",
            description="test",
            priority=GapPriority.LOW,
            confidence_score=0.6
        )
        
        priority = prioritizer.prioritize(
            gap, "I urgently need to know about this", 0.6
        )
        
        assert priority == GapPriority.CRITICAL


class TestEnrichmentClient:
    """Tests for EnrichmentClient."""

    @patch('src.mcp.enrichment_client.os.getenv')
    def test_client_not_configured(self, mock_getenv):
        """Test client without API key."""
        mock_getenv.return_value = None
        
        client = EnrichmentClient()
        
        assert client.is_configured() is False

    @patch('src.mcp.enrichment_client.os.getenv')
    def test_client_configured(self, mock_getenv):
        """Test client with API key."""
        mock_getenv.return_value = "test-api-key"
        
        client = EnrichmentClient()
        
        assert client.is_configured() is True

    def test_get_available_models(self):
        """Test getting available models."""
        client = EnrichmentClient()
        
        models = client.get_available_models()
        
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models


class TestPromptTemplateManager:
    """Tests for PromptTemplateManager."""

    def test_get_definition_prompt(self):
        """Test definition prompt generation."""
        manager = PromptTemplateManager()
        
        request = EnrichmentRequest(
            gap_type="definition",
            topic="Machine Learning",
            query_context="What is ML?",
            existing_sources=["ai/ml.md"]
        )
        
        prompt = manager.get_prompt("definition", request)
        
        assert "Machine Learning" in prompt
        assert "definition" in prompt.lower()
        assert "ai/ml.md" in prompt

    def test_get_comparison_prompt(self):
        """Test comparison prompt generation."""
        manager = PromptTemplateManager()
        
        request = EnrichmentRequest(
            gap_type="comparison",
            topic="SQL vs NoSQL",
            query_context="Compare them",
            existing_sources=[]
        )
        
        prompt = manager.get_prompt("comparison", request)
        
        assert "SQL vs NoSQL" in prompt
        assert "comparison" in prompt.lower()


class TestResponseValidator:
    """Tests for ResponseValidator."""

    def test_validate_empty_content(self):
        """Test validation of empty content."""
        validator = ResponseValidator()
        
        result = validator.validate("", "definition", EnrichmentRequest(
            gap_type="definition", topic="test", query_context="", existing_sources=[]
        ))
        
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_short_content(self):
        """Test validation of too short content."""
        validator = ResponseValidator()
        
        result = validator.validate("Short", "definition", EnrichmentRequest(
            gap_type="definition", topic="test", query_context="", existing_sources=[]
        ))
        
        assert result.is_valid is False

    def test_validate_valid_content(self):
        """Test validation of valid content."""
        validator = ResponseValidator()
        
        content = """
# Machine Learning

Machine learning is a type of artificial intelligence.

## Key Concepts
- Supervised learning
- Unsupervised learning
- Neural networks
"""
        
        result = validator.validate(content, "definition", EnrichmentRequest(
            gap_type="definition", topic="test", query_context="", existing_sources=[]
        ))
        
        assert result.is_valid is True
        assert result.quality_score >= 0.5


class TestContentDeduplicator:
    """Tests for ContentDeduplicator."""

    def test_exact_duplicate(self):
        """Test detection of exact duplicate."""
        dedup = ContentDeduplicator()
        
        existing = {"doc1.md": "This is test content"}
        
        result = dedup.check_duplicate("This is test content", existing)
        
        assert result.is_duplicate is True
        assert result.similarity_score == 1.0

    def test_no_duplicate(self):
        """Test when no duplicate exists."""
        dedup = ContentDeduplicator()
        
        existing = {"doc1.md": "This is original content"}
        
        result = dedup.check_duplicate("This is different content", existing)
        
        assert result.is_duplicate is False

    def test_similar_content(self):
        """Test detection of similar content."""
        dedup = ContentDeduplicator(similarity_threshold=0.7)
        
        existing = {"doc1.md": "Python is a programming language used for web development"}
        
        result = dedup.check_duplicate(
            "Python is a programming language used for data science",
            existing
        )
        
        assert result.is_duplicate is True
        assert result.similarity_score > 0.7


class TestConflictResolver:
    """Tests for ConflictResolver."""

    def test_detect_duplicate_headings(self):
        """Test detection of duplicate headings."""
        resolver = ConflictResolver()
        
        existing = "# Introduction\n\nContent here"
        new = "# Introduction\n\nNew content"
        
        conflicts = resolver.detect_conflicts(existing, new)
        
        assert any(c["type"] == "duplicate_heading" for c in conflicts)

    def test_resolve_replace(self):
        """Test replace strategy."""
        resolver = ConflictResolver()
        
        existing = "# Old Title\n\nOld content"
        new = "# New Title\n\nNew content"
        
        result = resolver.resolve(existing, new, MergeStrategy.REPLACE)
        
        assert result.success is True
        assert result.merged_content == new

    def test_resolve_preserve(self):
        """Test preserve strategy."""
        resolver = ConflictResolver()
        
        existing = "# Title\n\nExisting content"
        new = "# Title\n\nNew content"
        
        result = resolver.resolve(existing, new, MergeStrategy.PRESERVE)
        
        assert result.success is True
        assert result.merged_content == existing


class TestMergeEngine:
    """Tests for MergeEngine."""

    def test_merge_new_document(self):
        """Test merging when no existing content."""
        engine = MergeEngine()
        
        result = engine.merge(
            new_content="New content",
            existing_content=None
        )
        
        assert result.success is True
        assert result.merged_content == "New content"

    def test_merge_with_strategy(self):
        """Test merging with specific strategy."""
        engine = MergeEngine()
        
        result = engine.merge(
            new_content="New content",
            existing_content="Existing content",
            strategy=MergeStrategy.APPEND
        )
        
        assert result.success is True
        assert "New content" in result.merged_content
        assert "Existing content" in result.merged_content


class TestWriteManager:
    """Tests for WriteManager."""

    def test_write_operation_creation(self):
        """Test creating a write operation."""
        operation = WriteOperation(
            path="test.md",
            content="# Test",
            mode=WriteMode.CREATE,
            title="Test Document"
        )
        
        assert operation.path == "test.md"
        assert operation.mode == WriteMode.CREATE

    @patch('src.mcp.write_manager.Path.exists')
    def test_write_without_backup(self, mock_exists):
        """Test write without existing file."""
        mock_exists.return_value = False
        
        manager = WriteManager()
        operation = WriteOperation(
            path="knowledge/wiki/test.md",
            content="# Test",
            mode=WriteMode.CREATE,
            title="Test"
        )
        
        result = manager.write(operation)
        
        assert result.operation == WriteMode.CREATE


class TestEnrichmentOrchestrator:
    """Tests for EnrichmentOrchestrator."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = EnrichmentOrchestrator()
        
        assert orchestrator.gap_detector is not None
        assert orchestrator.merge_engine is not None
        assert orchestrator.write_manager is not None

    def test_enrich_without_llm_client(self):
        """Test enrichment when LLM client not configured."""
        orchestrator = EnrichmentOrchestrator(enable_writes=False)
        
        context = EnrichmentContext(
            query="What is AI?",
            confidence_score=0.3,
            retrieved_sources=[],
            context_summary=""
        )
        
        result = orchestrator.enrich(context)
        
        assert result.enrichment_triggered is False
        assert result.state.status == EnrichmentStatus.SKIPPED

    def test_enrich_high_confidence(self):
        """Test enrichment with high confidence (no enrichment needed)."""
        orchestrator = EnrichmentOrchestrator(enable_writes=False)
        
        context = EnrichmentContext(
            query="What is Python?",
            confidence_score=0.9,
            retrieved_sources=[{"path": "python.md", "content": "Python is..."}],
            context_summary="Python programming language"
        )
        
        result = orchestrator.enrich(context)
        
        assert result.enrichment_triggered is False
        assert result.state.status == EnrichmentStatus.SKIPPED

    def test_generate_file_path(self):
        """Test file path generation from topic."""
        orchestrator = EnrichmentOrchestrator()
        
        path = orchestrator._generate_file_path("Machine Learning Basics")
        
        assert "machine_learning_basics.md" in path
        assert path.startswith(orchestrator.wiki_path)


class TestEnrichmentState:
    """Tests for EnrichmentState."""

    def test_state_to_dict(self):
        """Test state serialization."""
        state = EnrichmentState(
            status=EnrichmentStatus.COMPLETED,
            correlation_id="test-123",
            gaps_detected=2,
            llm_calls_made=2,
            writes_completed=2
        )
        
        d = state.to_dict()
        
        assert d["status"] == "completed"
        assert d["correlation_id"] == "test-123"
        assert d["gaps_detected"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
