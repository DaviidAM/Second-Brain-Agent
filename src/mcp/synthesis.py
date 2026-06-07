"""
Response Synthesis - Phase 5: AI Response Generation
Generates natural language responses from retrieved context.
"""

from dataclasses import dataclass, field
from typing import Optional

from .context_builder import ContextWindow
from .query_analyzer import ParsedQuery


@dataclass
class SynthesisResult:
    """Result of response synthesis."""

    response: str
    citations: list[dict] = field(default_factory=list)
    tokens_used: int = 0
    model: str = ""


class CitationAttacher:
    """Attaches citations to generated responses."""

    def __init__(self, citation_format: str = "inline"):
        self.citation_format = citation_format

    def attach(self, response: str, sources: list[dict]) -> tuple[str, list[dict]]:
        """Attach citations to response."""
        if not sources:
            return response, []

        citations = []
        for i, source in enumerate(sources[:5]):
            citation = {
                "index": i + 1,
                "path": source.get("path", ""),
                "title": source.get("title", ""),
                "relevance_score": source.get("relevance_score", 0.0),
            }
            citations.append(citation)

        if self.citation_format == "inline":
            response = self._attach_inline(response, sources)
        elif self.citation_format == "footnote":
            response = self._attach_footnote(response, sources)
        else:
            response = self._attach_bracketed(response, sources)

        return response, citations

    def _attach_inline(self, response: str, sources: list[dict]) -> str:
        """Attach inline citations like [source]."""
        return response

    def _attach_footnote(self, response: str, sources: list[dict]) -> str:
        """Attach footnote style citations."""
        return response

    def _attach_bracketed(self, response: str, sources: list[dict]) -> str:
        """Attach bracketed citations like [1], [2]."""
        return response


class PromptBuilder:
    """Builds prompts for LLM synthesis."""

    def __init__(self):
        self._system_template = """You are a helpful AI assistant answering questions based on a knowledge base.

Instructions:
- Answer based ONLY on the provided context
- If the context doesn't contain enough information, say so clearly
- Use a conversational but professional tone
- Include relevant details from the sources
- Be concise but thorough"""

    def build_prompt(
        self,
        context_window: ContextWindow,
        parsed_query: ParsedQuery,
        include_citations: bool = True,
    ) -> tuple[str, str]:
        """Build system and user prompts for synthesis."""
        system = self._system_template

        if context_window.system_prompt:
            system += f"\n\nAdditional context:\n{context_window.system_prompt[:1000]}"

        user_parts = [
            f"Question: {parsed_query.original_query}",
            "",
            "Relevant information from knowledge base:",
        ]

        if context_window.user_prompt:
            user_parts.append(context_window.user_prompt[:3000])

        if include_citations:
            user_parts.append("")
            user_parts.append("Please cite your sources in your answer.")

        user = "\n".join(user_parts)

        return system, user

    def build_fallback_prompt(
        self, query: str, confidence_level: str
    ) -> tuple[str, str]:
        """Build prompt for fallback response."""
        system = "You are a helpful AI assistant."

        uncertainty_messages = {
            "very_low": "I don't have enough information to answer this question reliably.",
            "low": "I found some information but it's not complete enough to give a full answer.",
            "medium": "I found relevant information but there may be more to explore.",
        }

        user = f"""{uncertainty_messages.get(confidence_level, "")}

Question: {query}

Please provide what information you can, and clearly indicate any limitations."""

        return system, user


class ResponseSynthesizer:
    """
    Synthesizes natural language responses from retrieved context.
    """

    def __init__(self, citation_format: str = "bracketed", include_gaps: bool = True):
        self.prompt_builder = PromptBuilder()
        self.citation_attacher = CitationAttacher(citation_format)
        self.include_gaps = include_gaps

    def synthesize(
        self,
        context_window: ContextWindow,
        parsed_query: ParsedQuery,
        sources: list[dict],
        llm_callback=None,
        gap_info: Optional[dict] = None,
    ) -> SynthesisResult:
        """
        Synthesize response from context.

        Args:
            context_window: Built context window
            parsed_query: Parsed query
            sources: Retrieved sources
            llm_callback: Optional LLM callback for generation
            gap_info: Optional gap information

        Returns:
            SynthesisResult with response and citations
        """
        if llm_callback:
            system, user = self.prompt_builder.build_prompt(
                context_window, parsed_query
            )
            response_text = llm_callback(system, user)
        else:
            response_text = self._default_synthesize(context_window, parsed_query)

        response_text, citations = self.citation_attacher.attach(response_text, sources)

        if self.include_gaps and gap_info and gap_info.get("gaps"):
            response_text = self._add_gap_note(response_text, gap_info)

        return SynthesisResult(
            response=response_text,
            citations=citations,
            tokens_used=len(response_text.split()) * 1.3,
        )

    def _default_synthesize(
        self, context_window: ContextWindow, parsed_query: ParsedQuery
    ) -> str:
        """Default synthesis when no LLM available."""
        if not context_window.user_prompt:
            return "I don't have enough information to answer this question."

        snippets = context_window.user_prompt.split("---")
        if not snippets:
            return "I found some relevant information but need more context."

        relevant = snippets[0].strip() if snippets else ""

        if not relevant:
            return (
                "I found some relevant information but couldn't extract enough detail."
            )

        response = f"Based on the available information:\n\n{relevant[:1000]}"

        if len(relevant) > 1000:
            response += "\n\n[Content truncated due to length]"

        return response

    def _add_gap_note(self, response: str, gap_info: dict) -> str:
        """Add note about knowledge gaps."""
        gaps = gap_info.get("gaps", [])
        if not gaps:
            return response

        gap_types = [g.get("type", "unknown") for g in gaps]
        note = "\n\n---\n*Note: This answer may be incomplete. "

        if "missing_definition" in gap_types:
            note += "Some concepts lack clear definitions. "
        if "missing_example" in gap_types:
            note += "More examples could enhance this answer. "
        if "unknown_topic" in gap_types:
            note += "This topic may need additional documentation."

        note = note.rstrip() + "*"

        return response + note

    def synthesize_error(self, error: str, query: str) -> SynthesisResult:
        """Synthesize error response."""
        response = f"I encountered an error while processing your question: {error}\n\nPlease try again or rephrase your question."

        return SynthesisResult(response=response, citations=[], tokens_used=0)

    def synthesize_fallback(
        self, query: str, confidence_level: str, llm_callback=None
    ) -> SynthesisResult:
        """Synthesize fallback response for low confidence."""
        system, user = self.prompt_builder.build_fallback_prompt(
            query, confidence_level
        )

        if llm_callback:
            response_text = llm_callback(system, user)
        else:
            fallback_responses = {
                "very_low": "I don't have enough information in my knowledge base to answer this question reliably.",
                "low": "I found some information but it's not complete enough to give you a full answer.",
                "medium": "I found relevant information, but there may be more details available.",
            }
            response_text = fallback_responses.get(
                confidence_level, "I found some relevant information."
            )

        return SynthesisResult(
            response=response_text,
            citations=[],
            tokens_used=len(response_text.split()) * 1.3,
        )
