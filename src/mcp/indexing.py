"""
Indexing engines for keyword and vector search.
Phase 2: Knowledge Layer Foundation
"""

from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
from dataclasses import dataclass
import json
import math
import os
import re


@dataclass
class SearchResult:
    """Result from a search query."""
    filepath: str
    title: str
    relevance_score: float
    snippet: str
    vector_score: Optional[float] = None
    tags: List[str] = None
    last_modified: Optional[str] = None


class KeywordIndexer:
    """Builds and searches keyword index for markdown knowledge base."""
    
    @staticmethod
    def build_index(parsed_files: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build keyword index from parsed markdown files.
        
        Args:
            parsed_files: Dict mapping filepath -> ParsedFile (from parser.scan_directory)
            
        Returns:
            Index dict with keyword_index and file_metadata
        """
        keyword_index = defaultdict(list)
        file_metadata = {}
        
        for filepath, parsed in parsed_files.items():
            # Extract keywords from title, headings, tags, and content
            keywords = set()
            
            # Add title keywords
            title = parsed.frontmatter.get("title", "")
            title_keywords = KeywordIndexer._tokenize(title)
            keywords.update(title_keywords)
            
            # Add tag keywords
            tags = parsed.frontmatter.get("tags", [])
            keywords.update(tags)
            
            # Add content keywords (less important)
            content_keywords = KeywordIndexer._tokenize(parsed.content)
            # Add only high-frequency keywords from content
            keywords.update(KeywordIndexer._get_significant_keywords(content_keywords))
            
            # Add heading keywords
            for heading in parsed.metadata.get("headings", []):
                heading_keywords = KeywordIndexer._tokenize(heading.get("text", ""))
                keywords.update(heading_keywords)
            
            # Add to index
            for keyword in keywords:
                if keyword not in keyword_index[keyword]:
                    keyword_index[keyword].append(filepath)
            
            # Store file metadata
            file_metadata[filepath] = {
                "title": title,
                "created_at": parsed.frontmatter.get("created_at"),
                "last_modified": parsed.frontmatter.get("last_modified"),
                "author": parsed.frontmatter.get("author"),
                "word_count": parsed.metadata.get("word_count", 0),
                "tags": tags,
                "relations": parsed.frontmatter.get("relations", []),
                "source_type": parsed.frontmatter.get("source_type"),
            }
        
        return {
            "keyword_index": dict(keyword_index),
            "file_metadata": file_metadata,
            "total_files": len(parsed_files),
        }
    
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Tokenize text into keywords.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of lowercase keywords (2+ chars)
        """
        # Remove markdown formatting
        text = re.sub(r"[#*_`\[\]()]", " ", text)
        
        # Split on non-alphanumeric
        tokens = re.findall(r"\b\w+\b", text.lower())
        
        # Filter: remove short words and common stopwords
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "is", "are", "was", "were", "be", "been", "of", "by", "from", "as",
            "this", "that", "these", "those", "it", "if", "with", "about",
        }
        
        filtered = [t for t in tokens if len(t) >= 2 and t not in stopwords]
        return filtered
    
    @staticmethod
    def _get_significant_keywords(tokens: List[str], top_k: int = 20) -> List[str]:
        """Get most frequent keywords from token list."""
        from collections import Counter
        counter = Counter(tokens)
        return [token for token, _ in counter.most_common(top_k)]
    
    @staticmethod
    def search(query: str, index: Dict[str, Any], top_k: int = 5) -> List[SearchResult]:
        """
        Search the keyword index.
        
        Args:
            query: Search query string
            index: Keyword index from build_index
            top_k: Number of results to return
            
        Returns:
            List of SearchResult objects ranked by relevance
        """
        query_tokens = KeywordIndexer._tokenize(query)
        if not query_tokens:
            return []
        
        # Score files based on keyword matches
        file_scores = defaultdict(float)
        
        keyword_index = index["keyword_index"]
        file_metadata = index["file_metadata"]
        
        for token in query_tokens:
            matching_files = keyword_index.get(token, [])
            
            for filepath in matching_files:
                # Score higher if keyword is in title
                metadata = file_metadata.get(filepath, {})
                title = metadata.get("title", "")
                
                if token.lower() in title.lower():
                    file_scores[filepath] += 10.0  # Title match bonus
                elif token in metadata.get("tags", []):
                    file_scores[filepath] += 5.0   # Tag match bonus
                else:
                    file_scores[filepath] += 1.0   # Content match
        
        # Sort by score
        ranked_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Build results
        results = []
        for filepath, score in ranked_files[:top_k]:
            metadata = file_metadata.get(filepath, {})
            
            # Normalize score to 0-1
            normalized_score = min(score / 50.0, 1.0)
            
            # Generate snippet (first 150 chars)
            snippet = f"Document with {metadata.get('word_count', 0)} words"
            
            result = SearchResult(
                filepath=filepath,
                title=metadata.get("title", filepath),
                relevance_score=normalized_score,
                snippet=snippet,
                vector_score=None,
                tags=metadata.get("tags", []),
                last_modified=metadata.get("last_modified"),
            )
            results.append(result)
        
        return results
    
    @staticmethod
    def save_index(index: Dict[str, Any], index_path: str):
        """Save index to disk as JSON."""
        try:
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            with open(index_path, "w") as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save index: {e}")
    
    @staticmethod
    def load_index(index_path: str) -> Optional[Dict[str, Any]]:
        """Load index from disk."""
        if not os.path.exists(index_path):
            return None
        
        try:
            with open(index_path, "r") as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load index: {e}")


class WikilinkGraphBuilder:
    """Builds wikilink relationship graph."""
    
    @staticmethod
    def build_graph(parsed_files: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build wikilink graph from parsed files.
        
        Args:
            parsed_files: Dict mapping filepath -> ParsedFile
            
        Returns:
            Graph dict with nodes and edges
        """
        nodes = {}
        edges = []
        
        for filepath, parsed in parsed_files.items():
            # Add node
            metadata = parsed.metadata
            nodes[filepath] = {
                "title": parsed.frontmatter.get("title", ""),
                "tags": parsed.frontmatter.get("tags", []),
                "link_count": len(metadata.get("wikilinks", [])),
                "reference_count": 0,  # Will update below
            }
        
        # Build edges from wikilinks and relations
        for filepath, parsed in parsed_files.items():
            # Wikilinks
            for wikilink in parsed.metadata.get("wikilinks", []):
                target = wikilink.get("target", "")
                
                if target in nodes:
                    edges.append({
                        "source": filepath,
                        "target": target,
                        "type": "references",
                        "weight": 1,
                    })
                    nodes[target]["reference_count"] += 1
            
            # Relations from frontmatter
            for relation in parsed.frontmatter.get("relations", []):
                if relation in nodes:
                    edges.append({
                        "source": filepath,
                        "target": relation,
                        "type": "related",
                        "weight": 1,
                    })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }
    
    @staticmethod
    def get_related_files(
        filepath: str,
        graph: Dict[str, Any],
        max_depth: int = 2
    ) -> List[Tuple[str, int]]:
        """
        Find files related to given file through wikilinks.
        
        Args:
            filepath: Starting file
            graph: Wikilink graph
            max_depth: Max traversal depth
            
        Returns:
            List of (filepath, distance) tuples
        """
        nodes = graph.get("nodes", {})
        edges = graph.get("edges", [])
        
        if filepath not in nodes:
            return []
        
        # Build adjacency list
        adjacency = defaultdict(list)
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            adjacency[source].append(target)
        
        # BFS to find related files
        visited = {filepath: 0}
        queue = [(filepath, 0)]
        related = []
        
        while queue:
            current, depth = queue.pop(0)
            
            if depth < max_depth:
                for neighbor in adjacency.get(current, []):
                    if neighbor not in visited:
                        visited[neighbor] = depth + 1
                        queue.append((neighbor, depth + 1))
                        related.append((neighbor, depth + 1))
        
        # Sort by distance
        return sorted(related, key=lambda x: x[1])
    
    @staticmethod
    def get_graph_slice(
        graph: Dict[str, Any],
        query: Optional[str] = None,
        limit: int = 200
    ) -> Dict[str, Any]:
        """
        Get a slice of the graph (filtered by query if provided).
        
        Args:
            graph: Full wikilink graph
            query: Optional query to filter nodes
            limit: Max nodes to return
            
        Returns:
            Filtered graph dict
        """
        all_nodes = graph.get("nodes", {})
        all_edges = graph.get("edges", [])
        
        # Filter nodes by query
        if query:
            query_lower = query.lower()
            filtered_nodes = {
                path: node for path, node in all_nodes.items()
                if query_lower in path.lower() or query_lower in node.get("title", "").lower()
            }
        else:
            filtered_nodes = all_nodes
        
        # Limit nodes
        if len(filtered_nodes) > limit:
            # Keep top nodes by reference count
            filtered_nodes = dict(
                sorted(filtered_nodes.items(),
                       key=lambda x: x[1].get("reference_count", 0),
                       reverse=True)[:limit]
            )
        
        # Filter edges to only include filtered nodes
        filtered_edges = [
            edge for edge in all_edges
            if edge.get("source") in filtered_nodes and edge.get("target") in filtered_nodes
        ]
        
        return {
            "nodes": filtered_nodes,
            "edges": filtered_edges,
            "total_nodes": len(filtered_nodes),
            "total_edges": len(filtered_edges),
        }
    
    @staticmethod
    def save_graph(graph: Dict[str, Any], graph_path: str):
        """Save graph to disk as JSON."""
        try:
            os.makedirs(os.path.dirname(graph_path), exist_ok=True)
            with open(graph_path, "w") as f:
                json.dump(graph, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save graph: {e}")
    
    @staticmethod
    def load_graph(graph_path: str) -> Optional[Dict[str, Any]]:
        """Load graph from disk."""
        if not os.path.exists(graph_path):
            return None
        
        try:
            with open(graph_path, "r") as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load graph: {e}")
