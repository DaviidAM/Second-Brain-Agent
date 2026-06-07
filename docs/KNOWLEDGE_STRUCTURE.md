# Phase 2: Knowledge Base Architecture & Indexing

## Overview
This document defines the structure, conventions, and implementation details for the markdown-based knowledge base.

---

## Repository Structure

```
knowledge/
├── wiki/
│   ├── api-design/
│   │   ├── versioning-strategies.md
│   │   ├── authentication-patterns.md
│   │   └── deprecation-policy.md
│   ├── patterns/
│   │   ├── circuit-breaker.md
│   │   ├── retry-logic.md
│   │   └── fallback-patterns.md
│   ├── distributed-systems/
│   │   ├── consensus.md
│   │   └── failure-modes.md
│   └── index.md (optional: auto-generated TOC)
├── raw/
│   ├── sources/
│   │   ├── research-papers/
│   │   └── external-references/
│   └── archive/
└── .metadata/
    ├── index.json (keyword index)
    ├── embeddings.index (vector index - optional)
    └── graph.json (wikilink graph)
```

### Naming Conventions

**Directories**:
- Lowercase with hyphens: `api-design`, `distributed-systems`
- Represent major knowledge domains/categories
- Max 2 levels deep for discoverability

**Files**:
- Lowercase with hyphens: `versioning-strategies.md`
- Descriptive and specific (not generic names like `notes.md`)
- Match directory context (avoid redundancy)

**Examples**:
- ✅ `wiki/api-design/versioning-strategies.md`
- ✅ `wiki/patterns/circuit-breaker.md`
- ❌ `wiki/api-design/api-versioning.md` (redundant with directory)
- ❌ `wiki/my-notes.md` (too generic)

---

## Frontmatter Schema

Every markdown file in `wiki/` **must** include YAML frontmatter:

```yaml
---
title: "API Versioning Strategies"
author: "knowledge-system|manual"
created_at: "2026-05-10T09:15:00Z"
last_modified: "2026-05-15T14:30:00Z"
tags:
  - api-design
  - versioning
  - best-practices
relations:
  - wiki/patterns/backward-compatibility.md
  - wiki/api-design/deprecation-policy.md
confidence_score: 0.92
source_type: "manual|llm-generated"
llm_model: null
llm_prompt_hash: null
---
```

### Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Human-readable title (40-120 chars) |
| `author` | string | Yes | `knowledge-system` \| `manual` \| username |
| `created_at` | ISO 8601 | Yes | File creation timestamp (UTC) |
| `last_modified` | ISO 8601 | Yes | Last modification timestamp (UTC) |
| `tags` | array | Yes | 2-5 lowercase tags for categorization |
| `relations` | array | No | Paths to related documents |
| `confidence_score` | float 0-1 | No | Manual confidence rating (only for manual docs) |
| `source_type` | enum | Yes | `manual` \| `llm-generated` |
| `llm_model` | string | No | Model used if LLM-generated (e.g., `gpt-4-turbo`) |
| `llm_prompt_hash` | string | No | SHA-256 hash of prompt that generated this |

### Validation Rules

1. **title**: Must be 40-120 characters, no markdown
2. **author**: Must match `^[a-z0-9_-]+$` or reserved value
3. **tags**: 2-5 tags, lowercase, must match predefined tag taxonomy
4. **relations**: Valid paths must exist in knowledge base
5. **created_at ≤ last_modified**: Time ordering must be valid
6. **source_type**: Enum constraint (`manual` or `llm-generated`)

---

## Frontmatter Example: Manual Content

```yaml
---
title: "Circuit Breaker Pattern in Microservices"
author: "david"
created_at: "2026-05-10T09:15:00Z"
last_modified: "2026-06-05T16:20:00Z"
tags:
  - patterns
  - microservices
  - resilience
relations:
  - wiki/patterns/retry-logic.md
  - wiki/patterns/fallback-patterns.md
confidence_score: 0.95
source_type: "manual"
llm_model: null
llm_prompt_hash: null
---
```

## Frontmatter Example: LLM-Generated Content

```yaml
---
title: "Header-Based API Versioning Implementation"
author: "knowledge-system"
created_at: "2026-06-07T10:30:00Z"
last_modified: "2026-06-07T10:30:00Z"
tags:
  - api-design
  - versioning
  - implementation
relations:
  - wiki/api-design/versioning-strategies.md
confidence_score: 0.87
source_type: "llm-generated"
llm_model: "gpt-4-turbo"
llm_prompt_hash: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
---
```

---

## Markdown Content Guidelines

### Structure

```markdown
# Main Title (H1)

Brief intro paragraph (1-2 sentences explaining context).

## Section 1 (H2)

Content for section 1. Use clear, concise language.

### Subsection 1.1 (H3)

Detailed explanation if needed.

## Section 2

Content for section 2.

### Code Examples

Use fenced code blocks with language specification:

\`\`\`python
def circuit_breaker(failure_threshold=5):
    """Implementation example."""
    pass
\`\`\`

## Related Concepts

Brief mention of how this relates to:
- [[wiki/patterns/retry-logic.md|Retry Logic]]
- [[wiki/patterns/fallback-patterns.md|Fallback Patterns]]

## References

- [External Link](https://example.com)
- See [[wiki/api-design/versioning-strategies.md]] for more details
```

### Wikilink Format

Use double-bracket wikilinks for internal references:
- `[[wiki/patterns/circuit-breaker.md]]` — Link to file
- `[[wiki/patterns/circuit-breaker.md|Circuit Breaker Pattern]]` — Link with custom text

---

## Keyword Index Schema

The system maintains an in-memory keyword index:

```python
# .metadata/index.json (example)
{
  "keyword_index": {
    "api": ["wiki/api-design/versioning-strategies.md", "wiki/api-design/authentication-patterns.md"],
    "versioning": ["wiki/api-design/versioning-strategies.md"],
    "circuit-breaker": ["wiki/patterns/circuit-breaker.md"],
    "retry": ["wiki/patterns/retry-logic.md", "wiki/patterns/circuit-breaker.md"]
  },
  "file_metadata": {
    "wiki/api-design/versioning-strategies.md": {
      "title": "API Versioning Strategies",
      "created_at": "2026-05-10T09:15:00Z",
      "last_modified": "2026-05-15T14:30:00Z",
      "word_count": 856,
      "tags": ["api-design", "versioning", "best-practices"],
      "relations": ["wiki/patterns/backward-compatibility.md"]
    }
  },
  "last_indexed": "2026-06-07T10:00:00Z",
  "index_version": "2"
}
```

---

## Vector Index (Optional - Feature Flagged)

When vector embeddings are configured:

```python
# .metadata/embeddings.index (conceptual)
{
  "embedding_model": "text-embedding-3-small",
  "model_version": "1.0",
  "files": {
    "wiki/api-design/versioning-strategies.md": {
      "content_hash": "sha256_hash_of_content",
      "chunks": [
        {
          "chunk_id": 0,
          "text": "First 300-token chunk...",
          "embedding": [0.123, 0.456, ...],
          "start_pos": 0,
          "end_pos": 300
        }
      ]
    }
  },
  "last_updated": "2026-06-07T10:00:00Z"
}
```

---

## Wikilink Graph Schema

Maintains relationships between documents:

```python
# .metadata/graph.json
{
  "nodes": {
    "wiki/api-design/versioning-strategies.md": {
      "title": "API Versioning Strategies",
      "tags": ["api-design", "versioning"],
      "link_count": 5,
      "reference_count": 3
    }
  },
  "edges": [
    {
      "source": "wiki/api-design/versioning-strategies.md",
      "target": "wiki/patterns/backward-compatibility.md",
      "type": "references",
      "weight": 1
    }
  ],
  "last_updated": "2026-06-07T10:00:00Z"
}
```

---

## Implementation: Core Modules

### 1. Schema Validator (src/mcp/schema.py)

```python
# Validates frontmatter and structure
class FrontmatterSchema:
    REQUIRED_FIELDS = ["title", "author", "created_at", "last_modified", "tags", "source_type"]
    OPTIONAL_FIELDS = ["confidence_score", "relations", "llm_model", "llm_prompt_hash"]
    
    @staticmethod
    def validate(frontmatter: dict) -> tuple[bool, list[str]]:
        """Returns (is_valid, list_of_errors)"""
        pass
    
    @staticmethod
    def validate_file(filepath: str) -> tuple[bool, list[str]]:
        """Parse and validate a markdown file"""
        pass

class ContentValidator:
    @staticmethod
    def validate_wikilinks(content: str) -> tuple[bool, list[str]]:
        """Check that all wikilinks point to existing files"""
        pass
    
    @staticmethod
    def validate_markdown_structure(content: str) -> tuple[bool, list[str]]:
        """Check for proper heading hierarchy, code blocks, etc."""
        pass
```

### 2. Markdown Parser (src/mcp/parser.py)

```python
class MarkdownParser:
    @staticmethod
    def parse_file(filepath: str) -> dict:
        """
        Returns:
        {
            "frontmatter": dict,
            "content": str,
            "metadata": {
                "title": str,
                "word_count": int,
                "headings": list,
                "wikilinks": list,
                "external_links": list
            }
        }
        """
        pass
    
    @staticmethod
    def extract_wikilinks(content: str) -> list[str]:
        """Extract all [[wiki/path/file.md]] references"""
        pass
    
    @staticmethod
    def extract_headings(content: str) -> list[dict]:
        """Extract heading hierarchy for TOC"""
        pass
```

### 3. Indexing Engine (src/mcp/indexing.py)

```python
class KeywordIndexer:
    @staticmethod
    def build_index(knowledge_root: str) -> dict:
        """Scan all markdown files and build keyword index"""
        pass
    
    @staticmethod
    def update_index(filepath: str, index: dict) -> dict:
        """Update index after file modification"""
        pass
    
    @staticmethod
    def search(query: str, index: dict, top_k: int = 5) -> list[tuple[str, float]]:
        """Search index, return (filepath, score) tuples"""
        pass

class VectorIndexer:
    """Optional: activated by feature flag when embeddings configured"""
    
    @staticmethod
    def build_index(knowledge_root: str, embedding_model: str) -> dict:
        """Chunk files and generate embeddings"""
        pass
    
    @staticmethod
    def search(query_embedding: list[float], index: dict, top_k: int = 5) -> list[tuple[str, float]]:
        """Vector similarity search"""
        pass

class WikilinkGraphBuilder:
    @staticmethod
    def build_graph(knowledge_root: str) -> dict:
        """Build wikilink relationship graph"""
        pass
    
    @staticmethod
    def get_related_files(filepath: str, graph: dict, max_depth: int = 2) -> list[str]:
        """Find files related through wikilinks"""
        pass
```

### 4. Repository Manager (src/mcp/repository.py)

```python
class KnowledgeRepository:
    def __init__(self, root_path: str, enable_vector_index: bool = False):
        self.root_path = root_path
        self.keyword_index = None
        self.vector_index = None
        self.wikilink_graph = None
        self.enable_vector_index = enable_vector_index
    
    def initialize(self):
        """Load or build all indices"""
        pass
    
    def rescan(self, paths: list[str] = None):
        """Rebuild indices from scratch or update specific paths"""
        pass
    
    def get_file(self, filepath: str) -> dict:
        """Retrieve file with metadata"""
        pass
    
    def search_keyword(self, query: str, top_k: int = 5) -> list[dict]:
        """Keyword search"""
        pass
    
    def search_vector(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        """Vector search (if enabled)"""
        pass
    
    def hybrid_search(self, query: str, top_k: int = 5) -> list[dict]:
        """Keyword + optional vector search"""
        pass
    
    def validate_file(self, filepath: str) -> tuple[bool, list[str]]:
        """Validate markdown file structure"""
        pass
    
    def list_files(self, root: str = "wiki", recursive: bool = True) -> list[dict]:
        """List all files in tree structure"""
        pass
    
    def get_graph(self, limit: int = 200, query: str = None) -> dict:
        """Get wikilink graph"""
        pass
```

---

## Tag Taxonomy (Predefined)

```
api-design
distributed-systems
patterns
resilience
authentication
versioning
caching
monitoring
testing
documentation
microservices
performance
security
deployment
```

---

## Indexing Strategy

### Rebuild Trigger Points
1. Server startup → full rebuild
2. Manual rescan request → targeted rebuild
3. File system watch event (future) → incremental update

### Index Storage
- **Keyword index**: In-memory + `.metadata/index.json` backup
- **Vector index**: Optional, in `.metadata/embeddings.index`
- **Graph**: `.metadata/graph.json`

### Index Invalidation
- Index is invalidated if any file modification detected outside of MCP write operations
- Manual rescan rebuilds from scratch to ensure consistency

---

## Performance Considerations

- **Keyword search**: O(1) lookup + ranked result scoring → < 100ms typical
- **Vector search**: Approximate nearest neighbor (if enabled) → 200-500ms typical
- **Graph queries**: Pre-computed relationships → < 50ms typical
- **File parsing**: Lazy-load content only on explicit request

---

## Acceptance Criteria (Phase 2)

- [ ] Markdown parser correctly extracts frontmatter and validates against schema
- [ ] Keyword indexer builds and searches efficiently (< 100ms for 1000 files)
- [ ] Repository manager supports keyword + optional vector hybrid search
- [ ] Wikilink graph builder correctly identifies document relationships
- [ ] All indices can be rebuilt from scratch in < 5 seconds (for < 1000 files)
- [ ] Vector index feature flag allows clean MVP without embeddings dependency
- [ ] Tag taxonomy enforcement prevents invalid tags in frontmatter
- [ ] File validation catches frontmatter errors before persistence
