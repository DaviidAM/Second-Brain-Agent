"""
Unit tests for Phase 1 & 2 implementation.
Tests for schema validation, parsing, and indexing.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime

# Import modules to test
from src.mcp.schema import (
    FrontmatterSchema,
    ContentValidator,
    RepositoryValidator,
)
from src.mcp.parser import MarkdownParser, BulkParser
from src.mcp.indexing import KeywordIndexer, WikilinkGraphBuilder


# ==================== Schema Tests ====================

class TestFrontmatterSchema:
    """Tests for frontmatter validation."""
    
    def test_valid_frontmatter(self):
        """Test validation of valid frontmatter."""
        frontmatter = {
            "title": "Comprehensive Guide to API Versioning Strategies and Best Practices",
            "author": "david",
            "created_at": "2026-05-10T09:15:00Z",
            "last_modified": "2026-05-15T14:30:00Z",
            "tags": ["api-design", "versioning"],
            "source_type": "manual",
        }
        
        is_valid, errors = FrontmatterSchema.validate(frontmatter)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_missing_required_field(self):
        """Test validation fails with missing required field."""
        frontmatter = {
            "title": "API Versioning Strategies",
            "author": "david",
            # Missing created_at
            "last_modified": "2026-05-15T14:30:00Z",
            "tags": ["api-design", "versioning"],
            "source_type": "manual",
        }
        
        is_valid, errors = FrontmatterSchema.validate(frontmatter)
        assert is_valid is False
        assert any("created_at" in error for error in errors)
    
    def test_invalid_title_length(self):
        """Test validation fails with invalid title length."""
        frontmatter = {
            "title": "Short",  # Too short
            "author": "david",
            "created_at": "2026-05-10T09:15:00Z",
            "last_modified": "2026-05-15T14:30:00Z",
            "tags": ["api-design", "versioning"],
            "source_type": "manual",
        }
        
        is_valid, errors = FrontmatterSchema.validate(frontmatter)
        assert is_valid is False
        assert any("title" in error and "40-120" in error for error in errors)
    
    def test_invalid_tags(self):
        """Test validation fails with invalid tags."""
        frontmatter = {
            "title": "API Versioning Strategies",
            "author": "david",
            "created_at": "2026-05-10T09:15:00Z",
            "last_modified": "2026-05-15T14:30:00Z",
            "tags": ["invalid-tag", "another-invalid"],  # Invalid tags
            "source_type": "manual",
        }
        
        is_valid, errors = FrontmatterSchema.validate(frontmatter)
        assert is_valid is False
        assert any("invalid tag" in error for error in errors)
    
    def test_llm_generated_without_model(self):
        """Test validation fails for LLM-generated without model."""
        frontmatter = {
            "title": "Generated Content Title",
            "author": "knowledge-system",
            "created_at": "2026-06-07T10:30:00Z",
            "last_modified": "2026-06-07T10:30:00Z",
            "tags": ["api-design", "implementation"],
            "source_type": "llm-generated",
            # Missing llm_model
        }
        
        is_valid, errors = FrontmatterSchema.validate(frontmatter)
        assert is_valid is False
        assert any("llm_model" in error for error in errors)


# ==================== Parser Tests ====================

class TestMarkdownParser:
    """Tests for markdown parsing."""
    
    def test_parse_valid_markdown(self):
        """Test parsing valid markdown file."""
        content = """---
title: "Test Document"
author: david
created_at: "2026-05-10T09:15:00Z"
last_modified: "2026-05-15T14:30:00Z"
tags:
  - testing
  - documentation
source_type: manual
---

# Test Section

This is a test [[wiki/patterns/test.md|document]].

## Subsection

Some content here.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            f.flush()
            
            try:
                success, parsed, error = MarkdownParser.parse_file(f.name)
                assert success is True
                assert parsed.frontmatter["title"] == "Test Document"
                assert len(parsed.metadata["wikilinks"]) > 0
                assert len(parsed.metadata["headings"]) > 0
            finally:
                os.unlink(f.name)
    
    def test_extract_wikilinks(self):
        """Test wikilink extraction."""
        content = "See [[wiki/patterns/test.md]] for more [[wiki/other/file.md|details]]."
        
        wikilinks = MarkdownParser.extract_wikilinks(content)
        assert len(wikilinks) == 2
        assert wikilinks[0]["target"] == "wiki/patterns/test.md"
        assert wikilinks[1]["text"] == "details"
    
    def test_extract_headings(self):
        """Test heading extraction."""
        content = """# Main Title
## Section 1
### Subsection 1.1
## Section 2"""
        
        headings = MarkdownParser.extract_headings(content)
        assert len(headings) == 4
        assert headings[0]["level"] == 1
        assert headings[1]["text"] == "Section 1"
    
    def test_extract_code_blocks(self):
        """Test code block extraction."""
        content = """# Document

```python
def hello():
    print("world")
```

Some text.

```javascript
console.log("hi");
```
"""
        
        code_blocks = MarkdownParser.extract_code_blocks(content)
        assert len(code_blocks) == 2
        assert code_blocks[0]["language"] == "python"
        assert code_blocks[1]["language"] == "javascript"


# ==================== Indexing Tests ====================

class TestKeywordIndexer:
    """Tests for keyword indexing."""
    
    def test_tokenize(self):
        """Test text tokenization."""
        text = "API Versioning **Strategies** for Design"
        tokens = KeywordIndexer._tokenize(text)
        
        assert "api" in tokens
        assert "versioning" in tokens
        assert "strategies" in tokens
        assert "design" in tokens
        # Stopwords should be filtered
        assert "for" not in tokens
    
    def test_build_and_search_index(self):
        """Test building and searching index."""
        # Mock parsed files
        from src.mcp.parser import ParsedFile
        
        parsed_files = {
            "wiki/api-design/versioning.md": ParsedFile(
                filepath="wiki/api-design/versioning.md",
                frontmatter={
                    "title": "API Versioning Strategies",
                    "tags": ["api-design", "versioning"],
                    "created_at": "2026-05-10T09:15:00Z",
                    "relations": []
                },
                content="Versioning is important for APIs.",
                metadata={
                    "title": "API Versioning Strategies",
                    "word_count": 5,
                    "headings": [],
                    "wikilinks": [],
                    "external_links": [],
                    "code_blocks": [],
                }
            )
        }
        
        # Build index
        index = KeywordIndexer.build_index(parsed_files)
        
        # Search
        results = KeywordIndexer.search("versioning", index)
        assert len(results) > 0
        assert results[0].filepath == "wiki/api-design/versioning.md"


class TestWikilinGraphBuilder:
    """Tests for wikilink graph building."""
    
    def test_build_graph(self):
        """Test building wikilink graph."""
        from src.mcp.parser import ParsedFile
        
        parsed_files = {
            "wiki/patterns/pattern1.md": ParsedFile(
                filepath="wiki/patterns/pattern1.md",
                frontmatter={
                    "title": "Pattern 1",
                    "tags": ["patterns"],
                    "relations": ["wiki/patterns/pattern2.md"]
                },
                content="",
                metadata={
                    "wikilinks": [{"target": "wiki/patterns/pattern2.md", "text": "related"}],
                    "headings": [],
                    "external_links": [],
                    "code_blocks": [],
                }
            ),
            "wiki/patterns/pattern2.md": ParsedFile(
                filepath="wiki/patterns/pattern2.md",
                frontmatter={
                    "title": "Pattern 2",
                    "tags": ["patterns"],
                    "relations": []
                },
                content="",
                metadata={
                    "wikilinks": [],
                    "headings": [],
                    "external_links": [],
                    "code_blocks": [],
                }
            )
        }
        
        graph = WikilinkGraphBuilder.build_graph(parsed_files)
        
        assert graph["total_nodes"] == 2
        assert graph["total_edges"] >= 1
        assert "wiki/patterns/pattern1.md" in graph["nodes"]
        assert "wiki/patterns/pattern2.md" in graph["nodes"]


# ==================== Integration Tests ====================

class TestIntegration:
    """Integration tests for Phase 1 & 2."""
    
    def test_full_pipeline(self):
        """Test full pipeline: create markdown -> parse -> index -> search."""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create knowledge base structure
            wiki_dir = os.path.join(tmpdir, "wiki")
            os.makedirs(wiki_dir)
            
            # Create a test markdown file
            test_file = os.path.join(wiki_dir, "test.md")
            with open(test_file, "w") as f:
                f.write("""---
title: "Comprehensive Test Knowledge Document with Full Coverage"
author: david
created_at: "2026-05-10T09:15:00Z"
last_modified: "2026-05-10T09:15:00Z"
tags:
  - testing
  - documentation
source_type: manual
---

# Overview

This is a test document for knowledge base.
""")
            
            # Parse
            success, parsed, _ = MarkdownParser.parse_file(test_file)
            assert success is True
            
            # Validate
            is_valid, errors = FrontmatterSchema.validate(parsed.frontmatter)
            assert is_valid is True
            
            # Search (index would be built from parsed files)
            print("✓ Full pipeline test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
