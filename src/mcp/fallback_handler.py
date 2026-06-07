"""
Fallback Handler - Phase 5: AI Response Generation and Safety Controls
Provides deterministic fallback paths for error cases.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FallbackType(Enum):
    """Types of fallback responses."""

    NO_SOURCES = "no_sources"
    LOW_CONFIDENCE = "low_confidence"
    LLM_ERROR = "llm_error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class FallbackResponse:
    """Fallback response with metadata."""

    response: str
    fallback_type: FallbackType
    can_retry: bool = True
    retry_after: Optional[int] = None
    cached: bool = False


class DeterministicResponseGenerator:
    """Generates deterministic responses for known patterns."""

    def __init__(self):
        self._pattern_responses = {
            r"^what\s+is\s+": self._what_is_response,
            r"^how\s+do\s+i": self._how_to_response,
            r"^why\s+": self._why_response,
            r"^list\s+": self._list_response,
            r"^compare\s+": self._compare_response,
        }

    def generate(
        self, query: str, fallback_type: FallbackType, context: Optional[dict] = None
    ) -> str:
        """Generate deterministic fallback response."""
        context = context or {}

        if fallback_type == FallbackType.NO_SOURCES:
            return self._no_sources_response(query)
        elif fallback_type == FallbackType.LOW_CONFIDENCE:
            return self._low_confidence_response(query, context)
        elif fallback_type == FallbackType.LLM_ERROR:
            return self._llm_error_response(query)
        elif fallback_type == FallbackType.TIMEOUT:
            return self._timeout_response(query)
        elif fallback_type == FallbackType.RATE_LIMITED:
            return self._rate_limited_response(context)
        else:
            return self._unknown_error_response(query)

    def _no_sources_response(self, query: str) -> str:
        """Response when no sources found."""
        return f"""I couldn't find any relevant information in the knowledge base to answer your question: "{query}"

To help me assist you better:
- Try rephrasing your question
- Check if the relevant documents exist in the wiki
- Consider adding new content to the knowledge base"""

    def _low_confidence_response(self, query: str, context: dict) -> str:
        """Response for low confidence."""
        sources = context.get("source_count", 0)

        if sources == 0:
            return self._no_sources_response(query)

        return f"""I found some information but it's not complete enough to give you a confident answer about: "{query}"

Found {sources} related source(s) but they don't fully address your question.

Suggestions:
- Try a more specific question
- Check the related sources for more details
- The knowledge base may need more content on this topic"""

    def _llm_error_response(self, query: str) -> str:
        """Response when LLM fails."""
        return f"""I encountered an error while generating a detailed response for: "{query}"

The knowledge base search completed successfully, but the response synthesis failed.

What you can do:
- Try the same query again (temporary issue)
- Simplify your question
- Check the system logs for more details"""

    def _timeout_response(self, query: str) -> str:
        """Response when request times out."""
        return f"""The request timed out while processing: "{query}"

This may be due to:
- Complex query requiring extensive search
- Large knowledge base
- System load

Please try again with a simpler query or wait a moment."""

    def _rate_limited_response(self, context: dict) -> str:
        """Response when rate limited."""
        retry_after = context.get("retry_after", 60)

        return f"""Too many requests. Please wait before trying again.

Retry after: {retry_after} seconds

You can:
- Wait and try again
- Use a different endpoint
- Contact the administrator for rate limit increase"""

    def _unknown_error_response(self, query: str) -> str:
        """Response for unknown errors."""
        return f"""An unexpected error occurred while processing: "{query}"

Please try again or contact support if the problem persists."""

    def _what_is_response(self, query: str) -> str:
        """Deterministic response for 'what is' queries."""
        topic = re.sub(r"^what\s+is\s+", "", query.lower())
        return f"""I don't have specific information about "{topic}" in the knowledge base.

Try:
- Searching for related terms
- Adding a document about this topic
- Checking if the term is spelled differently"""

    def _how_to_response(self, query: str) -> str:
        """Deterministic response for 'how to' queries."""
        return f"""I don't have step-by-step instructions for: "{query}"

The knowledge base may not contain:
- Tutorial content
- Implementation guides
- How-to documentation

Consider adding a how-to guide to the wiki."""

    def _why_response(self, query: str) -> str:
        """Deterministic response for 'why' queries."""
        return f"""I don't have explanatory content for: "{query}"

This type of question typically requires:
- Conceptual documentation
- Architecture decision records
- Technical explanations

Consider adding explanatory content to the knowledge base."""

    def _list_response(self, query: str) -> str:
        """Deterministic response for 'list' queries."""
        return f"""I don't have list-based content for: "{query}"

Try:
- Searching for related topics
- Checking if there's a summary or overview document
- Adding a list document to the wiki"""

    def _compare_response(self, query: str) -> str:
        """Deterministic response for 'compare' queries."""
        return f"""I don't have comparison content for: "{query}"

Comparison content typically requires:
- Multiple documents covering different options
- Comparison tables or matrices
- Pros/cons analysis

Consider adding comparison documentation."""


class ErrorResponseBuilder:
    """Builds standardized error responses."""

    def __init__(self):
        self._error_messages = {
            400: "Bad request. Please check your input.",
            401: "Authentication required.",
            403: "Access denied.",
            404: "Resource not found.",
            429: "Rate limit exceeded. Please wait.",
            500: "Internal server error.",
            503: "Service temporarily unavailable.",
        }

    def build(
        self, error: str, status_code: int = 500, request_id: Optional[str] = None
    ) -> dict:
        """Build error response dict."""
        message = self._error_messages.get(status_code, "An error occurred")

        response = {
            "ok": False,
            "error": message,
            "details": error,
            "status_code": status_code,
        }

        if request_id:
            response["request_id"] = request_id

        return response

    def build_validation_error(
        self, field: str, message: str, request_id: Optional[str] = None
    ) -> dict:
        """Build validation error response."""
        response = {
            "ok": False,
            "error": "Validation failed",
            "field": field,
            "message": message,
        }

        if request_id:
            response["request_id"] = request_id

        return response


class FallbackHandler:
    """
    Main fallback handler for error cases and graceful degradation.
    """

    def __init__(self, cache_enabled: bool = True, cache_ttl: int = 3600):
        self.response_generator = DeterministicResponseGenerator()
        self.error_builder = ErrorResponseBuilder()
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self._response_cache: dict[str, tuple[str, float]] = {}

    def handle(
        self,
        fallback_type: FallbackType,
        query: str,
        context: Optional[dict] = None,
        request_id: Optional[str] = None,
    ) -> FallbackResponse:
        """
        Handle fallback case.

        Args:
            fallback_type: Type of fallback needed
            query: Original query
            context: Additional context
            request_id: Request ID for tracking

        Returns:
            FallbackResponse with appropriate message
        """
        cache_key = f"{fallback_type.value}:{query}"

        if self.cache_enabled and cache_key in self._response_cache:
            cached_response, timestamp = self._response_cache[cache_key]
            if (timestamp + self.cache_ttl) > self._get_timestamp():
                return FallbackResponse(
                    response=cached_response,
                    fallback_type=fallback_type,
                    can_retry=False,
                    cached=True,
                )

        response_text = self.response_generator.generate(query, fallback_type, context)

        can_retry = fallback_type in (
            FallbackType.LLM_ERROR,
            FallbackType.TIMEOUT,
            FallbackType.RATE_LIMITED,
        )

        retry_after = None
        if fallback_type == FallbackType.RATE_LIMITED:
            retry_after = context.get("retry_after", 60) if context else 60

        if self.cache_enabled:
            self._response_cache[cache_key] = (response_text, self._get_timestamp())

        return FallbackResponse(
            response=response_text,
            fallback_type=fallback_type,
            can_retry=can_retry,
            retry_after=retry_after,
            cached=False,
        )

    def handle_error(
        self, error: Exception, query: str, request_id: Optional[str] = None
    ) -> FallbackResponse:
        """Handle error based on exception type."""
        error_msg = str(error).lower()

        if "timeout" in error_msg:
            return self.handle(FallbackType.TIMEOUT, query, {}, request_id)
        elif "rate limit" in error_msg:
            return self.handle(FallbackType.RATE_LIMITED, query, {}, request_id)
        elif "api" in error_msg or "llm" in error_msg:
            return self.handle(FallbackType.LLM_ERROR, query, {}, request_id)
        else:
            return self.handle(FallbackType.UNKNOWN_ERROR, query, {}, request_id)

    def get_cached_response(
        self, query: str, fallback_type: FallbackType
    ) -> Optional[str]:
        """Get cached response if available."""
        cache_key = f"{fallback_type.value}:{query}"

        if cache_key in self._response_cache:
            cached_response, timestamp = self._response_cache[cache_key]
            if (timestamp + self.cache_ttl) > self._get_timestamp():
                return cached_response

        return None

    def clear_cache(self):
        """Clear the response cache."""
        self._response_cache.clear()

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time

        return time.time()
