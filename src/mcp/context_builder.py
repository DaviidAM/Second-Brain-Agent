"""
Context window builder for LLM prompting.
Phase 3: Read Pipeline - Context Building
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class ContextWindow:
    """Optimized context for LLM input."""
    main_content: str          # Primary document content
    supporting_docs: List[Dict[str, str]]  # Related documents
    citations: Dict[str, str]  # filepath -> source text mapping
    token_estimate: int        # Approximate tokens used
    quality_score: float       # 0-1 quality of context
    completeness: float        # 0-1 how well it covers the query


class ContextBuilder:
    """Builds optimized context windows for LLM prompting."""
    
    # Token estimation constants (rough)
    CHARS_PER_TOKEN = 4
    HEADING_OVERHEAD = 50  # Extra tokens for formatting
    
    @staticmethod
    def build_context(
        aggregated_results: List[Any],  # From retrieval orchestrator
        query: str,
        max_tokens: int = 3000,
    ) -> ContextWindow:
        """
        Build an optimized context window from retrieval results.
        
        Args:
            aggregated_results: Results from retrieval orchestrator
            query: Original query
            max_tokens: Maximum tokens for context
            
        Returns:
            ContextWindow optimized for LLM
        """
        if not aggregated_results:
            return ContextWindow(
                main_content="No relevant documents found.",
                supporting_docs=[],
                citations={},
                token_estimate=0,
                quality_score=0.0,
                completeness=0.0,
            )
        
        primary = aggregated_results[0]
        tokens_budget = max_tokens
        
        # Build main content
        main_content = ContextBuilder._build_main_section(
            primary,
            tokens_budget * 0.6,  # 60% for primary
        )
        
        tokens_used = ContextBuilder._estimate_tokens(main_content)
        tokens_budget -= tokens_used
        
        # Add supporting documents
        supporting_docs = []
        citations = {primary.primary_filepath: main_content}
        
        for related in primary.related_docs:
            if tokens_budget < 200:  # Minimum tokens for a doc section
                break
            
            section, tokens = ContextBuilder._build_supporting_section(
                related,
                tokens_budget,
            )
            
            supporting_docs.append(section)
            citations[related["filepath"]] = related["snippet"]
            tokens_budget -= tokens
            tokens_used += tokens
        
        # Calculate quality metrics
        quality_score = ContextBuilder._calculate_quality(
            aggregated_results[0],
            len(supporting_docs),
        )
        completeness = ContextBuilder._estimate_completeness(
            query,
            main_content,
            supporting_docs,
        )
        
        return ContextWindow(
            main_content=main_content,
            supporting_docs=supporting_docs,
            citations=citations,
            token_estimate=tokens_used,
            quality_score=quality_score,
            completeness=completeness,
        )
    
    @staticmethod
    def _build_main_section(primary: Any, token_budget: int) -> str:
        """Build main content section."""
        lines = [
            f"# {primary.primary_title}",
            "",
            primary.primary_snippet,
            "",
        ]
        
        # Add relationships
        if primary.related_docs:
            lines.append("## Related Concepts")
            for related in primary.related_docs[:3]:
                lines.append(f"- [[{related['filepath']}|{related['title']}]]")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _build_supporting_section(related: Dict[str, str], token_budget: int) -> Tuple[Dict[str, str], int]:
        """Build a supporting document section."""
        snippet = related["snippet"]
        
        # Truncate if necessary
        max_chars = token_budget * ContextBuilder.CHARS_PER_TOKEN
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars] + "..."
        
        section = {
            "title": related["title"],
            "filepath": related["filepath"],
            "snippet": snippet,
            "relevance": f"{related['relevance_score']:.2f}",
        }
        
        tokens = ContextBuilder._estimate_tokens(snippet)
        return section, tokens
    
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count."""
        return max(len(text) // ContextBuilder.CHARS_PER_TOKEN, 1)
    
    @staticmethod
    def _calculate_quality(primary: Any, supporting_count: int) -> float:
        """Calculate context quality score."""
        quality = primary.primary_score  # Base on relevance
        
        # Bonus for related documents
        quality += supporting_count * 0.05
        
        # Bonus for citation count
        citation_bonus = min(len(primary.sources) / 5.0 * 0.2, 0.2)
        quality += citation_bonus
        
        return min(quality, 1.0)
    
    @staticmethod
    def _estimate_completeness(query: str, main: str, supporting: List[Dict]) -> float:
        """Estimate how complete the context is for the query."""
        # Extract query keywords
        query_tokens = set(re.findall(r'\b\w+\b', query.lower()))
        query_tokens = {t for t in query_tokens if len(t) > 2}
        
        # Check coverage in main + supporting
        all_content = main + " ".join(s.get("snippet", "") for s in supporting)
        content_tokens = set(re.findall(r'\b\w+\b', all_content.lower()))
        
        # Calculate coverage
        if not query_tokens:
            return 0.5
        
        coverage = len(query_tokens & content_tokens) / len(query_tokens)
        return coverage


class PromptBuilder:
    """Builds final prompts for LLM from context."""
    
    @staticmethod
    def build_system_prompt() -> str:
        """Build system prompt for LLM."""
        return """You are a knowledgeable AI assistant with access to a curated knowledge base.

Your role is to:
1. Answer questions grounded in the provided context from the knowledge base
2. Cite specific documents when providing information
3. Acknowledge knowledge gaps clearly
4. Provide clear, structured answers
5. Ask for clarification if needed

When citing sources, use the format: [source-file-path]

If the knowledge base doesn't contain sufficient information, say so explicitly."""
    
    @staticmethod
    def build_user_prompt(
        query: str,
        context_window: ContextWindow,
        include_citations: bool = True,
    ) -> str:
        """
        Build user message with context.
        
        Args:
            query: User's original query
            context_window: Built context window
            include_citations: Include citation instructions
            
        Returns:
            Formatted prompt for LLM
        """
        lines = []
        
        # Add context header
        lines.append("## Knowledge Base Context")
        lines.append("")
        
        # Add main content
        lines.append("### Primary Information")
        lines.append(context_window.main_content)
        lines.append("")
        
        # Add supporting docs
        if context_window.supporting_docs:
            lines.append("### Supporting Information")
            for doc in context_window.supporting_docs:
                lines.append(f"#### {doc['title']}")
                lines.append(f"(Relevance: {doc['relevance']})")
                lines.append(f"Source: [{doc['filepath']}]")
                lines.append("")
                lines.append(doc["snippet"])
                lines.append("")
        
        # Add context metadata
        lines.append("---")
        lines.append(f"Context Quality: {context_window.quality_score:.2%}")
        lines.append(f"Completeness: {context_window.completeness:.2%}")
        lines.append(f"Sources Used: {', '.join(context_window.citations.keys())}")
        lines.append("")
        
        # Add user query
        lines.append("## Your Question")
        lines.append("")
        lines.append(query)
        
        if include_citations:
            lines.append("")
            lines.append("Please cite the knowledge base sources when you provide information.")
        
        return "\n".join(lines)


class ContextValidator:
    """Validates context quality before sending to LLM."""
    
    @staticmethod
    def validate(context_window: ContextWindow) -> tuple[bool, List[str]]:
        """
        Validate context window.
        
        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []
        
        # Check minimum quality
        if context_window.quality_score < 0.3:
            warnings.append(f"Low quality context (score: {context_window.quality_score:.2f})")
        
        # Check completeness
        if context_window.completeness < 0.3:
            warnings.append(f"Context may not fully cover the query (completeness: {context_window.completeness:.2%})")
        
        # Check token usage
        if context_window.token_estimate > 4000:
            warnings.append("Context window is large - may affect LLM performance")
        
        # Check citation count
        if len(context_window.citations) == 0:
            return False, ["No citations found in context"]
        
        if len(context_window.citations) == 1 and context_window.quality_score < 0.5:
            warnings.append("Only one source document - consider query reformulation")
        
        return len(warnings) == 0, warnings
