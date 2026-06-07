"""
Context Window Manager - Phase 5: AI Response Generation
Manages context window limits and token budgeting.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TruncationStrategy(Enum):
    """Strategies for truncating context."""
    PRIORITY_BASED = "priority_based"
    HEAD = "head"
    TAIL = "tail"
    SUMMARY = "summary"


@dataclass
class TokenBudget:
    """Token budget configuration."""
    max_tokens: int = 8000
    reserved_for_response: int = 2000
    min_context_tokens: int = 1000
    
    @property
    def available_for_context(self) -> int:
        return self.max_tokens - self.reserved_for_response


@dataclass
class SnippetBudget:
    """Budget allocation for a snippet."""
    path: str
    tokens: int
    priority: float = 1.0
    content: str = ""
    metadata: dict = field(default_factory=dict)


class TokenBudgetController:
    """Controls token budget allocation across snippets."""

    def __init__(self, budget: Optional[TokenBudget] = None):
        self.budget = budget or TokenBudget()

    def allocate(
        self,
        snippets: list[dict],
        priorities: Optional[list[float]] = None
    ) -> list[SnippetBudget]:
        """
        Allocate budget across snippets based on priority.
        
        Args:
            snippets: List of snippet dicts with 'content' and 'path'
            priorities: Optional priority scores (0-1) for each snippet
            
        Returns:
            List of SnippetBudget with allocated tokens
        """
        if not snippets:
            return []
        
        priorities = priorities or [1.0] * len(snippets)
        
        snippet_budgets = []
        for i, snippet in enumerate(snippets):
            content = snippet.get("content", "")
            tokens = self._estimate_tokens(content)
            
            snippet_budgets.append(SnippetBudget(
                path=snippet.get("path", ""),
                tokens=tokens,
                priority=priorities[i] if i < len(priorities) else 1.0,
                content=content,
                metadata=snippet
            ))
        
        snippet_budgets.sort(key=lambda x: x.priority, reverse=True)
        
        allocated = []
        remaining = self.budget.available_for_context
        
        for sb in snippet_budgets:
            if remaining <= self.budget.min_context_tokens:
                break
            
            allocated_tokens = min(sb.tokens, remaining)
            sb.tokens = allocated_tokens
            remaining -= allocated_tokens
            allocated.append(sb)
        
        return allocated

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        return int(len(text.split()) * 1.3)


class TruncationManager:
    """Manages context truncation strategies."""

    def __init__(self, strategy: TruncationStrategy = TruncationStrategy.PRIORITY_BASED):
        self.strategy = strategy

    def truncate(
        self,
        content: str,
        max_tokens: int
    ) -> str:
        """Truncate content to fit within token limit."""
        estimated_tokens = int(len(content.split()) * 1.3)
        
        if estimated_tokens <= max_tokens:
            return content
        
        if self.strategy == TruncationStrategy.HEAD:
            return self._truncate_head(content, max_tokens)
        elif self.strategy == TruncationStrategy.TAIL:
            return self._truncate_tail(content, max_tokens)
        elif self.strategy == TruncationStrategy.SUMMARY:
            return self._truncate_summary(content, max_tokens)
        else:
            return self._truncate_priority(content, max_tokens)

    def _truncate_head(self, content: str, max_tokens: int) -> str:
        """Keep beginning of content."""
        words = content.split()
        keep_words = int(max_tokens / 1.3)
        truncated = " ".join(words[:keep_words])
        return truncated + "\n\n[Content truncated...]"

    def _truncate_tail(self, content: str, max_tokens: int) -> str:
        """Keep end of content."""
        words = content.split()
        keep_words = int(max_tokens / 1.3)
        truncated = " ".join(words[-keep_words:])
        return "[...Content truncated]\n\n" + truncated

    def _truncate_summary(self, content: str, max_tokens: int) -> str:
        """Create summary of content."""
        words = content.split()
        keep_words = int(max_tokens / 1.3 / 2)
        
        head = " ".join(words[:keep_words])
        tail = " ".join(words[-keep_words:])
        
        return f"{head}\n\n[...]\n\n{tail}"

    def _truncate_priority(self, content: str, max_tokens: int) -> str:
        """Priority-based truncation - keep important sections."""
        sections = content.split("\n## ")
        
        if len(sections) <= 1:
            return self._truncate_head(content, max_tokens)
        
        result = []
        remaining_tokens = max_tokens
        
        for i, section in enumerate(sections):
            section_tokens = int(len(section.split()) * 1.3)
            
            if section_tokens <= remaining_tokens:
                result.append(section)
                remaining_tokens -= section_tokens
            else:
                result.append(self._truncate_head(section, remaining_tokens))
                break
        
        return "\n## ".join(result)


class ContextManager:
    """
    Main context window manager with token budgeting and truncation.
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        reserved_response_tokens: int = 2000,
        truncation_strategy: TruncationStrategy = TruncationStrategy.PRIORITY_BASED
    ):
        self.budget = TokenBudget(
            max_tokens=max_tokens,
            reserved_for_response=reserved_response_tokens
        )
        self.budget_controller = TokenBudgetController(self.budget)
        self.truncation_manager = TruncationManager(truncation_strategy)

    def prepare_context(
        self,
        snippets: list[dict],
        priorities: Optional[list[float]] = None
    ) -> tuple[str, list[dict]]:
        """
        Prepare context from snippets within token budget.
        
        Args:
            snippets: List of retrieved snippets
            priorities: Optional priority scores
            
        Returns:
            Tuple of (context_text, metadata)
        """
        allocated = self.budget_controller.allocate(snippets, priorities)
        
        context_parts = []
        metadata = []
        
        for sb in allocated:
            if sb.tokens >= self.budget.min_context_tokens:
                truncated = self.truncation_manager.truncate(
                    sb.content, sb.tokens
                )
                context_parts.append(truncated)
                
                metadata.append({
                    "path": sb.path,
                    "tokens_used": sb.tokens,
                    "priority": sb.priority,
                    "truncated": len(sb.content) > len(truncated)
                })
        
        context = "\n\n---\n\n".join(context_parts)
        
        return context, metadata

    def enforce_limit(
        self,
        context: str,
        max_tokens: Optional[int] = None
    ) -> str:
        """Enforce token limit on existing context."""
        max_tokens = max_tokens or self.budget.available_for_context
        return self.truncation_manager.truncate(context, max_tokens)

    def get_stats(self) -> dict:
        """Get context manager statistics."""
        return {
            "max_tokens": self.budget.max_tokens,
            "reserved_response": self.budget.reserved_for_response,
            "available_for_context": self.budget.available_for_context,
            "truncation_strategy": self.strategy.value if hasattr(self, 'strategy') else "priority_based"
        }

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens for text."""
        return self.budget_controller._estimate_tokens(text)
