"""
Markdown parser for extracting frontmatter, metadata, and structure.
Phase 2: Knowledge Layer Foundation
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import re
import os


@dataclass
class ParsedFile:
    """Result of parsing a markdown file."""
    filepath: str
    frontmatter: Dict[str, Any]
    content: str
    metadata: Dict[str, Any]


class MarkdownParser:
    """Parses markdown files and extracts structure."""
    
    @staticmethod
    def parse_file(filepath: str) -> Tuple[bool, ParsedFile | None, str]:
        """
        Parse a markdown file into frontmatter and content.
        
        Args:
            filepath: Path to markdown file
            
        Returns:
            (success, ParsedFile or None, error_message if failed)
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except Exception as e:
            return False, None, f"Failed to read file: {e}"
        
        # Split frontmatter and content
        if not raw_content.startswith("---"):
            return False, None, "File must start with YAML frontmatter (---)"
        
        try:
            parts = raw_content.split("---", 2)
            if len(parts) < 3:
                return False, None, "Invalid frontmatter: missing closing ---"
            
            frontmatter_str = parts[1].strip()
            markdown_content = parts[2].strip()
            
        except Exception as e:
            return False, None, f"Failed to split frontmatter: {e}"
        
        # Parse YAML frontmatter
        try:
            import yaml
            frontmatter = yaml.safe_load(frontmatter_str)
            if frontmatter is None:
                frontmatter = {}
        except Exception as e:
            return False, None, f"Failed to parse YAML frontmatter: {e}"
        
        # Extract metadata
        metadata = MarkdownParser._extract_metadata(filepath, markdown_content, frontmatter)
        
        parsed = ParsedFile(
            filepath=filepath,
            frontmatter=frontmatter,
            content=markdown_content,
            metadata=metadata
        )
        
        return True, parsed, ""
    
    @staticmethod
    def _extract_metadata(filepath: str, content: str, frontmatter: Dict) -> Dict[str, Any]:
        """Extract metadata from content and frontmatter."""
        metadata = {
            "filepath": filepath,
            "title": frontmatter.get("title", ""),
            "created_at": frontmatter.get("created_at"),
            "last_modified": frontmatter.get("last_modified"),
            "author": frontmatter.get("author"),
            "source_type": frontmatter.get("source_type"),
            "tags": frontmatter.get("tags", []),
            "relations": frontmatter.get("relations", []),
            "word_count": len(content.split()),
            "character_count": len(content),
            "headings": MarkdownParser.extract_headings(content),
            "wikilinks": MarkdownParser.extract_wikilinks(content),
            "external_links": MarkdownParser.extract_external_links(content),
            "code_blocks": MarkdownParser.extract_code_blocks(content),
        }
        
        # Add file stats
        try:
            stat = os.stat(filepath)
            metadata["file_size_bytes"] = stat.st_size
            metadata["file_modified"] = stat.st_mtime
        except:
            pass
        
        return metadata
    
    @staticmethod
    def extract_wikilinks(content: str) -> List[Dict[str, str]]:
        """
        Extract all [[wiki/path/file.md]] wikilinks from content.
        
        Returns:
            List of dicts: {"target": "wiki/path/file.md", "text": "display text", "anchor": null}
        """
        wikilinks = []
        
        # Pattern: [[target|text]] or [[target]]
        pattern = r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]"
        matches = re.finditer(pattern, content)
        
        for match in matches:
            target = match.group(1).strip()
            text = match.group(2).strip() if match.group(2) else None
            
            wikilinks.append({
                "target": target,
                "text": text or target,
                "anchor": None,  # Could be extended to support [[file.md#section]]
                "position": match.start()
            })
        
        return wikilinks
    
    @staticmethod
    def extract_external_links(content: str) -> List[Dict[str, str]]:
        """
        Extract all [text](url) markdown links.
        
        Returns:
            List of dicts: {"url": "https://...", "text": "display text"}
        """
        links = []
        
        # Pattern: [text](url)
        pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        matches = re.finditer(pattern, content)
        
        for match in matches:
            text = match.group(1)
            url = match.group(2)
            
            # Skip wikilinks (already handled)
            if not url.endswith(".md"):
                links.append({
                    "text": text,
                    "url": url,
                    "position": match.start()
                })
        
        return links
    
    @staticmethod
    def extract_headings(content: str) -> List[Dict[str, Any]]:
        """
        Extract heading hierarchy from content.
        
        Returns:
            List of dicts: {"level": 1, "text": "Heading Text", "position": 123}
        """
        headings = []
        lines = content.split("\n")
        
        for pos, line in enumerate(lines):
            # Match markdown headings
            match = re.match(r"^(#+)\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                
                # Create anchor (slugify)
                anchor = text.lower().replace(" ", "-").replace(".", "")
                anchor = re.sub(r"[^a-z0-9-]", "", anchor)
                
                headings.append({
                    "level": level,
                    "text": text,
                    "anchor": anchor,
                    "line_number": pos + 1,
                })
        
        return headings
    
    @staticmethod
    def extract_code_blocks(content: str) -> List[Dict[str, Any]]:
        """
        Extract code blocks with language info.
        
        Returns:
            List of dicts: {"language": "python", "code": "...", "line_start": 10}
        """
        code_blocks = []
        lines = content.split("\n")
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Match opening fence
            if re.match(r"^```(\w+)?$", line):
                match = re.match(r"^```(\w+)?$", line)
                language = match.group(1) or "text"
                start_line = i + 1
                
                # Find closing fence
                code_lines = []
                i += 1
                while i < len(lines):
                    if re.match(r"^```$", lines[i]):
                        break
                    code_lines.append(lines[i])
                    i += 1
                
                code_blocks.append({
                    "language": language,
                    "code": "\n".join(code_lines),
                    "line_start": start_line,
                    "line_end": i,
                })
            
            i += 1
        
        return code_blocks
    
    @staticmethod
    def extract_toc(content: str) -> str:
        """
        Generate table of contents from headings.
        
        Returns:
            Markdown formatted TOC
        """
        headings = MarkdownParser.extract_headings(content)
        if not headings:
            return ""
        
        lines = []
        for heading in headings:
            level = heading["level"]
            text = heading["text"]
            anchor = heading["anchor"]
            
            # Skip H1 (usually the document title)
            if level == 1:
                continue
            
            indent = "  " * (level - 2)
            lines.append(f"{indent}- [{text}](#{anchor})")
        
        return "\n".join(lines)
    
    @staticmethod
    def get_file_summary(filepath: str) -> Dict[str, Any]:
        """
        Quick summary of a file without full parsing.
        
        Returns:
            Dict with title, word_count, heading_count, link_count
        """
        success, parsed, error = MarkdownParser.parse_file(filepath)
        if not success:
            return {"error": error}
        
        return {
            "filepath": filepath,
            "title": parsed.metadata.get("title"),
            "word_count": parsed.metadata.get("word_count"),
            "heading_count": len(parsed.metadata.get("headings", [])),
            "wikilink_count": len(parsed.metadata.get("wikilinks", [])),
            "external_link_count": len(parsed.metadata.get("external_links", [])),
            "created_at": parsed.metadata.get("created_at"),
            "last_modified": parsed.metadata.get("last_modified"),
        }


class BulkParser:
    """Parser for scanning entire knowledge base."""
    
    @staticmethod
    def scan_directory(knowledge_root: str, pattern: str = "wiki") -> Dict[str, ParsedFile]:
        """
        Scan knowledge base directory and parse all markdown files.
        
        Args:
            knowledge_root: Root directory of knowledge base
            pattern: Subdirectory pattern to scan (default: "wiki")
            
        Returns:
            Dict mapping filepath -> ParsedFile
        """
        parsed_files = {}
        target_dir = os.path.join(knowledge_root, pattern)
        
        if not os.path.isdir(target_dir):
            return parsed_files
        
        # Recursively walk directory
        for root, dirs, files in os.walk(target_dir):
            for filename in files:
                if filename.endswith(".md"):
                    filepath = os.path.join(root, filename)
                    success, parsed, error = MarkdownParser.parse_file(filepath)
                    
                    if success and parsed:
                        # Store with relative path
                        rel_path = os.path.relpath(filepath, knowledge_root)
                        parsed_files[rel_path] = parsed
        
        return parsed_files
    
    @staticmethod
    def get_statistics(knowledge_root: str) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.
        
        Returns:
            Dict with total_files, total_words, average_heading_count, etc.
        """
        parsed_files = BulkParser.scan_directory(knowledge_root)
        
        if not parsed_files:
            return {"error": "No markdown files found"}
        
        total_words = 0
        total_chars = 0
        total_headings = 0
        total_wikilinks = 0
        all_tags = {}
        
        for parsed in parsed_files.values():
            total_words += parsed.metadata.get("word_count", 0)
            total_chars += parsed.metadata.get("character_count", 0)
            total_headings += len(parsed.metadata.get("headings", []))
            total_wikilinks += len(parsed.metadata.get("wikilinks", []))
            
            for tag in parsed.metadata.get("tags", []):
                all_tags[tag] = all_tags.get(tag, 0) + 1
        
        return {
            "total_files": len(parsed_files),
            "total_words": total_words,
            "total_characters": total_chars,
            "average_words_per_file": total_words // len(parsed_files) if parsed_files else 0,
            "total_headings": total_headings,
            "total_wikilinks": total_wikilinks,
            "unique_tags": list(all_tags.keys()),
            "tag_distribution": all_tags,
        }
