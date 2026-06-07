"""
Schema validation for markdown frontmatter and knowledge base structure.
Phase 2: Knowledge Layer Foundation
"""

from typing import Tuple, List, Dict, Any
from datetime import datetime
import re
from enum import Enum


class SourceType(str, Enum):
    """Valid source types for markdown files."""
    MANUAL = "manual"
    LLM_GENERATED = "llm-generated"


class FrontmatterSchema:
    """Validates YAML frontmatter for knowledge base files."""
    
    # Required fields that every file must have
    REQUIRED_FIELDS = {
        "title": str,
        "author": str,
        "created_at": str,  # ISO 8601
        "last_modified": str,  # ISO 8601
        "tags": list,
        "source_type": str,
    }
    
    # Optional fields
    OPTIONAL_FIELDS = {
        "confidence_score": float,
        "relations": list,
        "llm_model": str,
        "llm_prompt_hash": str,
    }
    
    # Predefined tag taxonomy
    VALID_TAGS = {
        "api-design",
        "distributed-systems",
        "patterns",
        "resilience",
        "authentication",
        "versioning",
        "caching",
        "monitoring",
        "testing",
        "documentation",
        "microservices",
        "performance",
        "security",
        "deployment",
        "best-practices",
        "implementation",
    }
    
    # Reserved authors
    RESERVED_AUTHORS = {"knowledge-system"}
    
    @staticmethod
    def validate(frontmatter: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate frontmatter dictionary.
        
        Returns:
            (is_valid, list_of_error_messages)
        """
        errors: List[str] = []
        
        # Check required fields
        for field, expected_type in FrontmatterSchema.REQUIRED_FIELDS.items():
            if field not in frontmatter:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(frontmatter[field], expected_type):
                errors.append(
                    f"Field '{field}' has wrong type: expected {expected_type.__name__}, "
                    f"got {type(frontmatter[field]).__name__}"
                )
        
        # Check optional fields types
        for field, expected_type in FrontmatterSchema.OPTIONAL_FIELDS.items():
            if field in frontmatter and not isinstance(frontmatter[field], expected_type):
                errors.append(
                    f"Optional field '{field}' has wrong type: expected {expected_type.__name__}, "
                    f"got {type(frontmatter[field]).__name__}"
                )
        
        if errors:
            return False, errors
        
        # Validate specific field constraints
        validation_errors = FrontmatterSchema._validate_field_constraints(frontmatter)
        errors.extend(validation_errors)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _validate_field_constraints(frontmatter: Dict[str, Any]) -> List[str]:
        """Validate individual field constraints."""
        errors: List[str] = []
        
        # Validate title
        title = frontmatter.get("title", "")
        if not (40 <= len(title) <= 120):
            errors.append(f"title must be 40-120 characters, got {len(title)}")
        if any(c in title for c in "#*_`"):
            errors.append("title must not contain markdown formatting characters")
        
        # Validate author
        author = frontmatter.get("author", "")
        if author not in FrontmatterSchema.RESERVED_AUTHORS:
            if not re.match(r"^[a-z0-9_-]+$", author):
                errors.append(f"author must match ^[a-z0-9_-]+$, got '{author}'")
        
        # Validate tags
        tags = frontmatter.get("tags", [])
        if not (2 <= len(tags) <= 5):
            errors.append(f"must have 2-5 tags, got {len(tags)}")
        for tag in tags:
            if tag not in FrontmatterSchema.VALID_TAGS:
                errors.append(
                    f"invalid tag '{tag}'. Valid tags: {', '.join(sorted(FrontmatterSchema.VALID_TAGS))}"
                )
        
        # Validate source_type
        source_type = frontmatter.get("source_type", "")
        if source_type not in [st.value for st in SourceType]:
            errors.append(f"source_type must be '{SourceType.MANUAL}' or '{SourceType.LLM_GENERATED}'")
        
        # Validate timestamps
        try:
            created_at = datetime.fromisoformat(frontmatter.get("created_at", "").replace("Z", "+00:00"))
            last_modified = datetime.fromisoformat(frontmatter.get("last_modified", "").replace("Z", "+00:00"))
            if created_at > last_modified:
                errors.append("created_at must be <= last_modified")
        except ValueError as e:
            errors.append(f"Invalid ISO 8601 timestamp: {e}")
        
        # Validate confidence_score if present
        if "confidence_score" in frontmatter:
            score = frontmatter["confidence_score"]
            if not (0.0 <= score <= 1.0):
                errors.append(f"confidence_score must be between 0 and 1, got {score}")
        
        # Validate relations if present
        if "relations" in frontmatter:
            relations = frontmatter["relations"]
            for relation in relations:
                if not isinstance(relation, str):
                    errors.append(f"relations must be list of strings, got {type(relation)}")
                if not relation.endswith(".md"):
                    errors.append(f"relation path must end with .md: {relation}")
        
        # Validate LLM fields consistency
        source_type = frontmatter.get("source_type", "")
        if source_type == SourceType.MANUAL.value:
            if frontmatter.get("llm_model") is not None:
                errors.append("manual sources should not have llm_model set")
        elif source_type == SourceType.LLM_GENERATED.value:
            if not frontmatter.get("llm_model"):
                errors.append("llm-generated sources must specify llm_model")
        
        return errors
    
    @staticmethod
    def to_yaml(frontmatter: Dict[str, Any]) -> str:
        """
        Convert frontmatter dict to YAML string suitable for file frontmatter.
        
        Args:
            frontmatter: Validated frontmatter dictionary
            
        Returns:
            YAML string (without --- delimiters)
        """
        import yaml
        
        lines = []
        
        # Order: required fields first
        for field in ["title", "author", "created_at", "last_modified", "tags", "relations", "confidence_score", "source_type", "llm_model", "llm_prompt_hash"]:
            if field in frontmatter:
                value = frontmatter[field]
                if isinstance(value, str):
                    lines.append(f"{field}: \"{value}\"")
                elif isinstance(value, list):
                    lines.append(f"{field}:")
                    for item in value:
                        lines.append(f"  - {item}")
                elif isinstance(value, (int, float)):
                    lines.append(f"{field}: {value}")
                else:
                    lines.append(f"{field}: {yaml.dump(value).strip()}")
        
        return "\n".join(lines)


class ContentValidator:
    """Validates markdown content structure and integrity."""
    
    @staticmethod
    def validate_wikilinks(content: str, knowledge_base_files: set) -> Tuple[bool, List[str]]:
        """
        Check that all wikilinks point to existing files.
        
        Args:
            content: Markdown content
            knowledge_base_files: Set of valid file paths in knowledge base
            
        Returns:
            (is_valid, list_of_error_messages)
        """
        errors: List[str] = []
        
        # Pattern: [[wiki/path/file.md|optional text]] or [[wiki/path/file.md]]
        wikilink_pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
        matches = re.findall(wikilink_pattern, content)
        
        for wikilink in matches:
            filepath = wikilink.strip()
            if filepath not in knowledge_base_files:
                errors.append(f"Wikilink references non-existent file: {filepath}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_markdown_structure(content: str) -> Tuple[bool, List[str]]:
        """
        Check markdown structure (heading hierarchy, code blocks, etc.).
        
        Args:
            content: Markdown content
            
        Returns:
            (is_valid, list_of_error_messages)
        """
        errors: List[str] = []
        lines = content.split("\n")
        
        heading_levels = []
        in_code_block = False
        
        for i, line in enumerate(lines, 1):
            # Track code blocks
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
            
            # Check heading hierarchy
            if line.startswith("#") and not in_code_block:
                level = len(line) - len(line.lstrip("#"))
                
                # H1 should appear exactly once at the top
                if level == 1:
                    if heading_levels and heading_levels[0] == 1:
                        errors.append(f"Line {i}: Multiple H1 headings (should appear once)")
                
                # Check for proper hierarchy (skip 1-2 levels)
                if heading_levels and level > heading_levels[-1] + 1:
                    errors.append(
                        f"Line {i}: Heading hierarchy skip from H{heading_levels[-1]} to H{level}"
                    )
                
                heading_levels.append(level)
        
        # Check for unclosed code blocks
        if in_code_block:
            errors.append("Unclosed code block (``` without closing ```)")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_file(filepath: str, knowledge_base_files: set = None) -> Tuple[bool, List[str]]:
        """
        Full validation of a markdown file (frontmatter + content).
        
        Args:
            filepath: Path to markdown file
            knowledge_base_files: Set of valid file paths for wikilink validation
            
        Returns:
            (is_valid, list_of_error_messages)
        """
        errors: List[str] = []
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return False, [f"Failed to read file: {e}"]
        
        # Parse frontmatter
        if not content.startswith("---"):
            return False, ["File must start with YAML frontmatter (---)"]
        
        try:
            parts = content.split("---", 2)
            if len(parts) < 3:
                return False, ["Invalid frontmatter: missing closing ---"]
            
            frontmatter_str = parts[1]
            markdown_content = parts[2]
            
            import yaml
            frontmatter = yaml.safe_load(frontmatter_str)
            
        except Exception as e:
            return False, [f"Failed to parse frontmatter: {e}"]
        
        # Validate frontmatter
        fm_valid, fm_errors = FrontmatterSchema.validate(frontmatter)
        errors.extend(fm_errors)
        
        # Validate markdown content
        md_valid, md_errors = ContentValidator.validate_markdown_structure(markdown_content)
        errors.extend(md_errors)
        
        # Validate wikilinks if knowledge_base_files provided
        if knowledge_base_files:
            wl_valid, wl_errors = ContentValidator.validate_wikilinks(markdown_content, knowledge_base_files)
            errors.extend(wl_errors)
        
        return len(errors) == 0, errors


class RepositoryValidator:
    """Validates overall repository structure."""
    
    @staticmethod
    def validate_structure(knowledge_root: str) -> Tuple[bool, List[str]]:
        """
        Validate repository structure (directories, required files).
        
        Args:
            knowledge_root: Path to knowledge base root
            
        Returns:
            (is_valid, list_of_error_messages)
        """
        errors: List[str] = []
        
        required_dirs = ["wiki", ".metadata"]
        for dir_name in required_dirs:
            dir_path = f"{knowledge_root}/{dir_name}"
            try:
                import os
                if not os.path.isdir(dir_path):
                    errors.append(f"Missing required directory: {dir_path}")
            except Exception as e:
                errors.append(f"Failed to check directory {dir_path}: {e}")
        
        return len(errors) == 0, errors
