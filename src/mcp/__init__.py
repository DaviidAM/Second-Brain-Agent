"""
MCP (Model Context Protocol) - Knowledge Assistant Server
Phase 1-3: Product contract, knowledge layer, & read pipeline
"""

__version__ = "0.2.0"
__author__ = "David Alba"

# Phase 1-2: Core layers
from .schema import FrontmatterSchema, ContentValidator, RepositoryValidator
from .parser import MarkdownParser, BulkParser, ParsedFile
from .indexing import KeywordIndexer, WikilinkGraphBuilder, SearchResult

# Phase 3: Read pipeline
from .query_analyzer import (
    QueryAnalyzer,
    QueryValidator,
    QueryOptimizer,
    ParsedQuery,
    QueryIntent,
    QueryComplexity,
)
from .retrieval import (
    HybridRetriever,
    CrossDocumentAggregator,
    ScoreNormalizer,
    RetrievalOrchestrator,
    RetrievalMode,
    RetrievalContext,
    AggregatedResult,
)
from .repository import KnowledgeRepository, RepositoryStats
from .context_builder import ContextBuilder, PromptBuilder, ContextValidator, ContextWindow

__all__ = [
    # Phase 1-2
    "FrontmatterSchema",
    "ContentValidator",
    "RepositoryValidator",
    "MarkdownParser",
    "BulkParser",
    "ParsedFile",
    "KeywordIndexer",
    "WikilinkGraphBuilder",
    "SearchResult",
    # Phase 3
    "QueryAnalyzer",
    "QueryValidator",
    "QueryOptimizer",
    "ParsedQuery",
    "QueryIntent",
    "QueryComplexity",
    "HybridRetriever",
    "CrossDocumentAggregator",
    "ScoreNormalizer",
    "RetrievalOrchestrator",
    "RetrievalMode",
    "RetrievalContext",
    "AggregatedResult",
    "KnowledgeRepository",
    "RepositoryStats",
    "ContextBuilder",
    "PromptBuilder",
    "ContextValidator",
    "ContextWindow",
]
