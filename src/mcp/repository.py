"""
Knowledge repository manager with initialization and lifecycle.
Phase 3: Read Pipeline - Repository Management
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import os
import json
from datetime import datetime

from .parser import MarkdownParser, BulkParser, ParsedFile
from .indexing import KeywordIndexer, WikilinkGraphBuilder
from .schema import FrontmatterSchema, ContentValidator


@dataclass
class RepositoryStats:
    """Statistics about the knowledge repository."""
    total_files: int
    total_words: int
    total_characters: int
    average_file_size: int
    unique_tags: List[str]
    domains: List[str]
    last_indexed: str
    index_health: float  # 0-1 health score


class KnowledgeRepository:
    """Manages the knowledge base lifecycle."""
    
    REQUIRED_DIRS = ["wiki", ".metadata", "raw/sources", "raw/archive"]
    METADATA_FILES = {
        "index.json": "Keyword index",
        "graph.json": "Wikilink graph",
        "embeddings.index": "Vector embeddings (optional)",
        "stats.json": "Repository statistics",
    }
    
    def __init__(self, root_path: str, enable_vector_index: bool = False):
        """
        Initialize repository manager.
        
        Args:
            root_path: Root directory of knowledge base
            enable_vector_index: Enable vector search (Phase 2 feature flag)
        """
        self.root_path = root_path
        self.enable_vector_index = enable_vector_index
        
        # In-memory indices
        self.keyword_index: Optional[Dict] = None
        self.vector_index: Optional[Dict] = None
        self.wikilink_graph: Optional[Dict] = None
        self.parsed_files: Dict[str, ParsedFile] = {}
        
        # State
        self._initialized = False
        self._dirty = False  # Indices out of sync with files
    
    def initialize(self) -> Tuple[bool, List[str]]:
        """
        Initialize repository structure.
        
        Creates necessary directories and loads indices.
        
        Returns:
            (success, list_of_errors)
        """
        errors = []
        
        # Create required directories
        try:
            for dir_name in self.REQUIRED_DIRS:
                dir_path = os.path.join(self.root_path, dir_name)
                os.makedirs(dir_path, exist_ok=True)
            
            # Initialize git if not already
            git_dir = os.path.join(self.root_path, ".git")
            if not os.path.exists(git_dir):
                try:
                    import subprocess
                    subprocess.run(
                        ["git", "init"],
                        cwd=self.root_path,
                        capture_output=True,
                        timeout=5,
                    )
                except Exception as e:
                    errors.append(f"Git initialization warning: {e}")
        
        except Exception as e:
            return False, [f"Failed to create directories: {e}"]
        
        # Load existing indices
        try:
            self.keyword_index = KeywordIndexer.load_index(
                os.path.join(self.root_path, ".metadata", "index.json")
            )
            self.wikilink_graph = WikilinkGraphBuilder.load_graph(
                os.path.join(self.root_path, ".metadata", "graph.json")
            )
        except Exception as e:
            errors.append(f"Warning loading indices: {e}")
        
        # If no indices exist, build them
        if self.keyword_index is None or self.wikilink_graph is None:
            success, build_errors = self.rescan()
            errors.extend(build_errors)
        
        self._initialized = True
        return len(errors) == 0, errors
    
    def rescan(self, paths: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        """
        Rebuild indices from scratch or update specific paths.
        
        Args:
            paths: Specific paths to rescan (None = full rescan)
            
        Returns:
            (success, list_of_errors)
        """
        errors = []
        
        try:
            # Parse all markdown files
            wiki_dir = os.path.join(self.root_path, "wiki")
            self.parsed_files = BulkParser.scan_directory(self.root_path, "wiki")
            
            if not self.parsed_files:
                errors.append("No markdown files found in wiki/")
            
            # Build keyword index
            try:
                self.keyword_index = KeywordIndexer.build_index(self.parsed_files)
                KeywordIndexer.save_index(
                    self.keyword_index,
                    os.path.join(self.root_path, ".metadata", "index.json")
                )
            except Exception as e:
                errors.append(f"Failed to build keyword index: {e}")
            
            # Build wikilink graph
            try:
                self.wikilink_graph = WikilinkGraphBuilder.build_graph(self.parsed_files)
                WikilinkGraphBuilder.save_graph(
                    self.wikilink_graph,
                    os.path.join(self.root_path, ".metadata", "graph.json")
                )
            except Exception as e:
                errors.append(f"Failed to build wikilink graph: {e}")
            
            # Save statistics
            try:
                stats = self.get_statistics()
                stats_dict = {
                    "total_files": stats.total_files,
                    "total_words": stats.total_words,
                    "average_file_size": stats.average_file_size,
                    "unique_tags": stats.unique_tags,
                    "last_indexed": stats.last_indexed,
                }
                
                with open(
                    os.path.join(self.root_path, ".metadata", "stats.json"),
                    "w"
                ) as f:
                    json.dump(stats_dict, f, indent=2)
            except Exception as e:
                errors.append(f"Failed to save statistics: {e}")
            
            self._dirty = False
        
        except Exception as e:
            return False, [f"Rescan failed: {e}"]
        
        return len([e for e in errors if "Failed" in e]) == 0, errors
    
    def get_file(self, filepath: str) -> Optional[Tuple[ParsedFile, List[str]]]:
        """
        Retrieve parsed file.
        
        Args:
            filepath: Relative path (e.g., "wiki/patterns/circuit-breaker.md")
            
        Returns:
            (ParsedFile, list_of_errors) or None if not found
        """
        # Validate path safety
        if ".." in filepath or filepath.startswith("/"):
            return None
        
        # Check if already parsed
        if filepath in self.parsed_files:
            return self.parsed_files[filepath], []
        
        # Try to parse directly
        full_path = os.path.join(self.root_path, filepath)
        if not os.path.exists(full_path):
            return None
        
        success, parsed, error = MarkdownParser.parse_file(full_path)
        if not success:
            return None, [error]
        
        return parsed, []
    
    def search_keyword(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Keyword search.
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of search results
        """
        if not self.keyword_index:
            return []
        
        results = KeywordIndexer.search(query, self.keyword_index, top_k)
        
        # Convert to dicts
        return [
            {
                "filepath": r.filepath,
                "title": r.title,
                "snippet": r.snippet,
                "relevance_score": r.relevance_score,
                "tags": r.tags or [],
            }
            for r in results
        ]
    
    def search_vector(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Vector search (if enabled).
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results
            
        Returns:
            List of search results
        """
        if not self.enable_vector_index or not self.vector_index:
            return []
        
        # Phase 2 feature: would implement vector search here
        return []
    
    def hybrid_search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Hybrid keyword + vector search.
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            Dict with results and metadata
        """
        keyword_results = self.search_keyword(query, top_k)
        vector_results = self.search_vector([], top_k) if self.enable_vector_index else []
        
        return {
            "mode": "hybrid" if vector_results else "keyword",
            "keyword_results": keyword_results,
            "vector_results": vector_results,
            "combined_results": keyword_results,  # Phase 3 will implement merging
        }
    
    def list_files(self, root: str = "wiki", recursive: bool = True) -> Dict[str, Any]:
        """
        List all files in tree structure.
        
        Args:
            root: Root directory to list
            recursive: Include subdirectories
            
        Returns:
            Tree structure dict
        """
        root_path = os.path.join(self.root_path, root)
        
        if not os.path.isdir(root_path):
            return {"error": f"Directory not found: {root}"}
        
        def build_tree(path: str) -> Dict[str, Any]:
            """Recursively build tree structure."""
            name = os.path.basename(path)
            
            if os.path.isdir(path):
                children = []
                try:
                    for item in sorted(os.listdir(path)):
                        if item.startswith("."):
                            continue
                        item_path = os.path.join(path, item)
                        if recursive or not os.path.isdir(item_path):
                            children.append(build_tree(item_path))
                except PermissionError:
                    pass
                
                return {
                    "name": name,
                    "isDir": True,
                    "children": children,
                    "size": sum(
                        os.path.getsize(os.path.join(path, f))
                        for f in os.listdir(path)
                        if os.path.isfile(os.path.join(path, f))
                    ),
                }
            else:
                return {
                    "name": name,
                    "isDir": False,
                    "size": os.path.getsize(path),
                    "lastModified": datetime.fromtimestamp(
                        os.path.getmtime(path)
                    ).isoformat(),
                }
        
        return build_tree(root_path)
    
    def get_graph(self, limit: int = 200, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Get wikilink graph (optionally filtered).
        
        Args:
            limit: Max nodes to return
            query: Optional filter query
            
        Returns:
            Graph dict
        """
        if not self.wikilink_graph:
            return {"error": "Graph not initialized"}
        
        return WikilinkGraphBuilder.get_graph_slice(
            self.wikilink_graph,
            query,
            limit,
        )
    
    def validate_file(self, filepath: str) -> Tuple[bool, List[str]]:
        """
        Validate a markdown file.
        
        Args:
            filepath: Path to file
            
        Returns:
            (is_valid, list_of_errors)
        """
        full_path = os.path.join(self.root_path, filepath)
        
        # Get all valid file paths for wikilink validation
        valid_files = set(self.parsed_files.keys())
        
        return ContentValidator.validate_file(full_path, valid_files)
    
    def get_statistics(self) -> RepositoryStats:
        """Get repository statistics."""
        stats = BulkParser.get_statistics(self.root_path)
        
        # Calculate health score
        health = 0.5
        if stats["total_files"] > 10:
            health += 0.2
        if len(stats["unique_tags"]) > 5:
            health += 0.15
        if stats["total_words"] > 10000:
            health += 0.15
        
        return RepositoryStats(
            total_files=stats["total_files"],
            total_words=stats["total_words"],
            total_characters=stats["total_characters"],
            average_file_size=stats["average_words_per_file"],
            unique_tags=stats["unique_tags"],
            domains=list(set(
                tag for tags_list in [
                    parsed.frontmatter.get("tags", [])
                    for parsed in self.parsed_files.values()
                ]
                for tag in tags_list
            )),
            last_indexed=datetime.now().isoformat(),
            index_health=min(health, 1.0),
        )
    
    def is_initialized(self) -> bool:
        """Check if repository is initialized."""
        return self._initialized and self.keyword_index is not None
    
    def is_healthy(self) -> bool:
        """Check repository health."""
        if not self._initialized:
            return False
        
        # Check required files exist
        for dir_name in self.REQUIRED_DIRS:
            if not os.path.isdir(os.path.join(self.root_path, dir_name)):
                return False
        
        # Check indices loaded
        if self.keyword_index is None or self.wikilink_graph is None:
            return False
        
        return True
