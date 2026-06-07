"""
Query analysis and intent detection.
Phase 3: Read Pipeline - Query Analysis
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re


class QueryIntent(str, Enum):
    """Query intent classification."""
    SEARCH = "search"              # Simple search for documents
    EXPLANATION = "explanation"    # Explain a concept
    COMPARISON = "comparison"      # Compare multiple concepts
    IMPLEMENTATION = "implementation"  # How to implement something
    TROUBLESHOOTING = "troubleshooting"  # Debug/fix an issue
    REFERENCE = "reference"        # Look up specific information
    SYNTHESIS = "synthesis"        # Combine multiple concepts
    UNKNOWN = "unknown"


class QueryComplexity(str, Enum):
    """Query complexity level."""
    SIMPLE = "simple"              # Single topic, single intent
    MODERATE = "moderate"          # Multiple topics or aspects
    COMPLEX = "complex"            # Multi-domain reasoning required


@dataclass
class ParsedQuery:
    """Result of query analysis."""
    original_query: str
    intent: QueryIntent
    complexity: QueryComplexity
    entities: List[str]            # Key concepts/topics
    keywords: List[str]            # Search keywords
    domains: List[str]             # Knowledge domains (python, ia, etc)
    relations: List[str]           # Suggested related files
    required_context_tokens: int   # Estimated context needed
    confidence: float              # 0-1 confidence in parsing


class QueryAnalyzer:
    """Analyzes and structures user queries."""
    
    # Intent keywords mapping
    INTENT_KEYWORDS = {
        QueryIntent.EXPLANATION: ["explain", "what is", "tell me", "describe", "define", "how does"],
        QueryIntent.COMPARISON: ["compare", "difference", "vs", "versus", "similar", "different"],
        QueryIntent.IMPLEMENTATION: ["how to", "implement", "build", "create", "write", "setup"],
        QueryIntent.TROUBLESHOOTING: ["fix", "debug", "error", "issue", "problem", "help"],
        QueryIntent.REFERENCE: ["what are", "list", "show", "find", "get", "lookup"],
        QueryIntent.SYNTHESIS: ["combine", "relate", "connection", "integrate", "cross", "link"],
    }
    
    # Domain keywords
    DOMAIN_KEYWORDS = {
        "python": ["python", "py", "flask", "django", "fastapi", "async", "pip"],
        "ia": ["ai", "machine learning", "llm", "neural", "model", "training", "prompt", "transformer"],
        "backend": ["backend", "api", "database", "server", "microservice", "cache", "queue"],
        "security": ["security", "encrypt", "auth", "token", "ssl", "tls", "vulnerability"],
        "patterns": ["pattern", "design", "architecture", "best practice", "anti-pattern"],
    }
    
    @staticmethod
    def analyze(query: str) -> ParsedQuery:
        """
        Analyze a user query and extract structure.
        
        Args:
            query: User's question or search query
            
        Returns:
            ParsedQuery with intent, entities, keywords, etc.
        """
        query_lower = query.lower()
        
        # Detect intent
        intent = QueryAnalyzer._detect_intent(query_lower)
        
        # Extract entities (key nouns/concepts)
        entities = QueryAnalyzer._extract_entities(query)
        
        # Extract keywords for search
        keywords = QueryAnalyzer._extract_keywords(query_lower)
        
        # Detect domains
        domains = QueryAnalyzer._detect_domains(query_lower)
        
        # Determine complexity
        complexity = QueryAnalyzer._assess_complexity(query, intent, entities)
        
        # Estimate context needed
        context_tokens = QueryAnalyzer._estimate_context_tokens(complexity, len(entities))
        
        # Calculate confidence
        confidence = QueryAnalyzer._calculate_confidence(intent, entities, keywords)
        
        parsed = ParsedQuery(
            original_query=query,
            intent=intent,
            complexity=complexity,
            entities=entities,
            keywords=keywords,
            domains=domains,
            relations=[],  # Will be filled by retrieval phase
            required_context_tokens=context_tokens,
            confidence=confidence,
        )
        
        return parsed
    
    @staticmethod
    def _detect_intent(query_lower: str) -> QueryIntent:
        """Detect query intent from keywords."""
        for intent, keywords in QueryAnalyzer.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return intent
        
        return QueryIntent.REFERENCE  # Default to reference
    
    @staticmethod
    def _extract_entities(query: str) -> List[str]:
        """Extract key entities (nouns/concepts) from query."""
        entities = []
        
        # Match quoted phrases first
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)
        
        # Extract capitalized terms (likely proper nouns/concepts)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(capitalized)
        
        # Extract common noun phrases (nouns followed by other nouns)
        noun_patterns = [
            r'\b(\w+\s+pattern)\b',
            r'\b(\w+\s+architecture)\b',
            r'\b(\w+\s+design)\b',
            r'\b(\w+\s+model)\b',
            r'\b(\w+\s+algorithm)\b',
        ]
        for pattern in noun_patterns:
            matches = re.findall(pattern, query.lower())
            entities.extend(matches)
        
        # Deduplicate and return
        return list(set(entities))[:10]  # Top 10 entities
    
    @staticmethod
    def _extract_keywords(query_lower: str) -> List[str]:
        """Extract search keywords from query."""
        # Split on common stopwords and punctuation
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "is", "are", "was", "were", "be", "by", "from", "with", "about",
            "how", "what", "when", "where", "why", "which", "who", "does",
        }
        
        # Tokenize
        tokens = re.findall(r'\b\w+\b', query_lower)
        
        # Filter stopwords and short words
        keywords = [
            t for t in tokens 
            if len(t) > 2 and t not in stopwords
        ]
        
        return keywords[:8]  # Top 8 keywords
    
    @staticmethod
    def _detect_domains(query_lower: str) -> List[str]:
        """Detect knowledge domains mentioned in query."""
        detected = []
        
        for domain, keywords in QueryAnalyzer.DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    detected.append(domain)
                    break  # Only add each domain once
        
        return detected or ["backend"]  # Default to backend
    
    @staticmethod
    def _assess_complexity(query: str, intent: QueryIntent, entities: List[str]) -> QueryComplexity:
        """Assess query complexity."""
        # Heuristics for complexity
        query_length = len(query.split())
        entity_count = len(entities)
        keyword_count = len(query.split())
        
        if query_length > 30 or entity_count > 5:
            return QueryComplexity.COMPLEX
        elif query_length > 15 or entity_count > 2:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.SIMPLE
    
    @staticmethod
    def _estimate_context_tokens(complexity: QueryComplexity, entity_count: int) -> int:
        """Estimate context window tokens needed."""
        base_tokens = {
            QueryComplexity.SIMPLE: 1500,
            QueryComplexity.MODERATE: 2500,
            QueryComplexity.COMPLEX: 4000,
        }
        
        # Add extra tokens for multiple entities
        extra = entity_count * 300
        
        return base_tokens.get(complexity, 2000) + extra
    
    @staticmethod
    def _calculate_confidence(intent: QueryIntent, entities: List[str], keywords: List[str]) -> float:
        """Calculate confidence in query understanding."""
        score = 0.5  # Base confidence
        
        # Intent clarity
        if intent != QueryIntent.UNKNOWN:
            score += 0.2
        
        # Entity extraction
        if len(entities) > 0:
            score += min(0.15, len(entities) * 0.05)
        
        # Keyword extraction
        if len(keywords) > 2:
            score += 0.15
        
        return min(score, 1.0)


class QueryValidator:
    """Validates query structure and safety."""
    
    @staticmethod
    def validate(query: str) -> tuple[bool, str]:
        """
        Validate query for safety and format.
        
        Returns:
            (is_valid, error_message if invalid)
        """
        # Empty check
        if not query or len(query.strip()) == 0:
            return False, "Query cannot be empty"
        
        # Length check
        if len(query) > 500:
            return False, "Query exceeds maximum length (500 characters)"
        
        # Minimum words
        if len(query.split()) < 2:
            return False, "Query must contain at least 2 words"
        
        # Check for SQL injection patterns (basic)
        dangerous_patterns = ["DROP", "DELETE", "INSERT", "UPDATE", "UNION"]
        if any(pattern in query.upper() for pattern in dangerous_patterns):
            return False, "Query contains potentially dangerous SQL patterns"
        
        # Check for path traversal
        if ".." in query or "//" in query:
            return False, "Query contains potentially dangerous path patterns"
        
        return True, ""


class QueryOptimizer:
    """Optimizes queries for better retrieval."""
    
    @staticmethod
    def expand_query(parsed_query: ParsedQuery) -> List[str]:
        """
        Generate alternative query formulations for better retrieval.
        
        Args:
            parsed_query: ParsedQuery object
            
        Returns:
            List of alternative queries
        """
        alternatives = [parsed_query.original_query]
        
        # If complex, try simpler versions
        if parsed_query.complexity == QueryComplexity.COMPLEX:
            # Use only keywords
            keyword_query = " ".join(parsed_query.keywords[:5])
            alternatives.append(keyword_query)
            
            # Use entities
            if parsed_query.entities:
                entity_query = " ".join(parsed_query.entities[:3])
                alternatives.append(entity_query)
        
        # Add domain-specific queries
        for domain in parsed_query.domains:
            domain_query = f"{parsed_query.original_query} {domain}"
            alternatives.append(domain_query)
        
        return alternatives[:5]  # Return top 5 alternatives
