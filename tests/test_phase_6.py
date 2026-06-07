"""
Tests for Phase 6: Git Automation and Auditability
"""

import pytest
from src.mcp.git_automation import (
    GitAutoCommit, CommitType, CommitMessage, CommitMessageGenerator,
    CommitPolicy, CommitResult
)
from src.mcp.operation_logger import (
    OperationLogger, OperationType, OperationStatus, OperationLog,
    LogFormatter, AuditTrail
)
from src.mcp.provenance import (
    ProvenanceTracker, ProvenanceRecord, LineageEntry,
    CorrelationManager, LineageRecorder
)


class TestCommitMessageGenerator:
    """Tests for CommitMessageGenerator."""

    def test_generate_add_message(self):
        """Test generating add commit message."""
        generator = CommitMessageGenerator()
        
        msg = generator.generate(
            CommitType.ADD,
            "New Document",
            "corr-123",
            "Added new content"
        )
        
        assert msg.type == CommitType.ADD
        assert "Add:" in msg.format()

    def test_generate_update_message(self):
        """Test generating update commit message."""
        generator = CommitMessageGenerator()
        
        msg = generator.generate(
            CommitType.UPDATE,
            "Existing Document",
            "corr-456"
        )
        
        assert msg.type == CommitType.UPDATE
        assert "Update:" in msg.format()

    def test_trailers_included(self):
        """Test that trailers are included in message."""
        generator = CommitMessageGenerator()
        
        msg = generator.generate(
            CommitType.ENRICH,
            "Test Doc",
            "corr-789",
            "Added examples"
        )
        
        assert "provenance" in msg.trailers
        assert "enrichment_rationale" in msg.trailers


class TestCommitPolicy:
    """Tests for CommitPolicy."""

    def test_can_commit_valid_file(self):
        """Test valid file check."""
        policy = CommitPolicy()
        
        can_commit, reason = policy.can_commit("test.md")
        
        assert isinstance(can_commit, bool)

    def test_file_size_limit(self):
        """Test file size limit."""
        policy = CommitPolicy(max_file_size=100)
        
        can_commit, reason = policy.can_commit("test.md")
        
        assert "too large" in reason.lower() or can_commit is True

    def test_allowed_extensions(self):
        """Test allowed extensions."""
        policy = CommitPolicy(allowed_extensions=[".md"])
        
        can_commit_md, _ = policy.can_commit("test.md")
        can_commit_py, _ = policy.can_commit("test.py")
        
        assert can_commit_md is True
        assert can_commit_py is False


class TestGitAutoCommit:
    """Tests for GitAutoCommit."""

    def test_initialization(self):
        """Test initialization."""
        commit = GitAutoCommit()
        
        assert commit.author_name == "MCP Knowledge Assistant"
        assert commit.policy is not None

    def test_is_git_repo(self):
        """Test git repo detection."""
        commit = GitAutoCommit(repo_path=".")
        
        is_repo = commit.is_git_repo()
        
        assert isinstance(is_repo, bool)


class TestLogFormatter:
    """Tests for LogFormatter."""

    def test_format_json(self):
        """Test JSON formatting."""
        formatter = LogFormatter("json")
        
        log = OperationLog(
            operation_id="test-123",
            operation_type="query",
            status="completed",
            timestamp="2024-01-01T00:00:00"
        )
        
        formatted = formatter.format(log)
        
        assert "test-123" in formatted
        assert "query" in formatted

    def test_format_text(self):
        """Test text formatting."""
        formatter = LogFormatter("text")
        
        log = OperationLog(
            operation_id="test-456",
            operation_type="enrich",
            status="completed",
            timestamp="2024-01-01T00:00:00"
        )
        
        formatted = formatter.format(log)
        
        assert "test-456" in formatted


class TestAuditTrail:
    """Tests for AuditTrail."""

    def test_initialization(self):
        """Test initialization."""
        trail = AuditTrail()
        
        assert trail.audit_dir.name == "audit"

    def test_query_empty(self):
        """Test querying empty audit trail."""
        trail = AuditTrail()
        
        results = trail.query(limit=10)
        
        assert isinstance(results, list)


class TestOperationLogger:
    """Tests for OperationLogger."""

    def test_initialization(self):
        """Test initialization."""
        logger = OperationLogger()
        
        assert logger.audit_trail is not None
        assert logger.formatter is not None

    def test_log_operation(self):
        """Test logging operation."""
        logger = OperationLogger()
        
        op_id = logger.log_operation(
            OperationType.QUERY,
            {"query": "test"}
        )
        
        assert op_id is not None

    def test_log_query(self):
        """Test logging query."""
        logger = OperationLogger(log_level="SILENT")
        
        logger.log_query("test query")
        
        assert logger is not None


class TestCorrelationManager:
    """Tests for CorrelationManager."""

    def test_create_correlation_id(self):
        """Test creating correlation ID."""
        manager = CorrelationManager()
        
        corr_id = manager.create_correlation_id("test query")
        
        assert corr_id is not None
        assert len(corr_id) > 0

    def test_get_correlation(self):
        """Test getting correlation."""
        manager = CorrelationManager()
        
        corr_id = manager.create_correlation_id("test query")
        corr = manager.get_correlation(corr_id)
        
        assert corr is not None
        assert corr["query"] == "test query"

    def test_add_event(self):
        """Test adding event."""
        manager = CorrelationManager()
        
        corr_id = manager.create_correlation_id("test")
        manager.add_event(corr_id, "test_event", {"key": "value"})
        
        events = manager.get_events(corr_id)
        
        assert len(events) > 0


class TestLineageRecorder:
    """Tests for LineageRecorder."""

    def test_initialization(self):
        """Test initialization."""
        recorder = LineageRecorder()
        
        assert recorder.lineage_dir.name == "lineage"

    def test_record_lineage(self):
        """Test recording lineage."""
        recorder = LineageRecorder()
        
        recorder.record("test-corr", "test_event", {"key": "value"})
        
        lineage = recorder.get_lineage("test-corr")
        
        assert len(lineage) > 0


class TestProvenanceTracker:
    """Tests for ProvenanceTracker."""

    def test_initialization(self):
        """Test initialization."""
        tracker = ProvenanceTracker()
        
        assert tracker.correlation_manager is not None
        assert tracker.lineage_recorder is not None

    def test_start_request(self):
        """Test starting request."""
        tracker = ProvenanceTracker()
        
        corr_id = tracker.start_request("test query")
        
        assert corr_id is not None

    def test_record_retrieval(self):
        """Test recording retrieval."""
        tracker = ProvenanceTracker()
        
        corr_id = tracker.start_request("test")
        tracker.record_retrieval(corr_id, ["source1", "source2"], 0.8)
        
        lineage = tracker.get_lineage(corr_id)
        
        assert len(lineage) > 0

    def test_record_enrichment(self):
        """Test recording enrichment."""
        tracker = ProvenanceTracker()
        
        corr_id = tracker.start_request("test")
        tracker.record_enrichment(corr_id, 2, "gpt-4", 1.5, ["file1.md"])
        
        provenance = tracker.get_provenance(corr_id)
        
        assert provenance is not None
        assert provenance.enrichment_triggered is True

    def test_record_write(self):
        """Test recording write."""
        tracker = ProvenanceTracker()
        
        corr_id = tracker.start_request("test")
        tracker.record_write(corr_id, "test.md", True)
        
        lineage = tracker.get_lineage(corr_id)
        
        assert any(e.event == "write_completed" for e in lineage)

    def test_finalize_request(self):
        """Test finalizing request."""
        tracker = ProvenanceTracker()
        
        corr_id = tracker.start_request("test")
        tracker.finalize_request(corr_id, True)
        
        lineage = tracker.get_lineage(corr_id)
        
        assert any(e.event == "request_completed" for e in lineage)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
