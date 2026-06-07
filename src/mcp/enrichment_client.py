"""
LLM Enrichment Client - Phase 4: Write and Enrichment Pipeline
Calls external LLM API to generate content for knowledge gaps.
"""

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EnrichmentModel(Enum):
    """Available LLM models for enrichment."""

    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_35_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"


class GapTypePrompt(Enum):
    """Prompt templates for different gap types."""

    MISSING_DEFINITION = "definition"
    INCOMPLETE_COMPARISON = "comparison"
    OUTDATED_INFO = "update"
    MISSING_EXAMPLE = "example"
    UNKNOWN_TOPIC = "explanation"
    PARTIAL_EXPLANATION = "expansion"
    MISSING_PREREQUISITES = "prerequisites"


@dataclass
class EnrichmentRequest:
    """Request for LLM enrichment."""

    gap_type: str
    topic: str
    query_context: str
    existing_sources: list[str]
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2000


@dataclass
class EnrichmentResponse:
    """Response from LLM enrichment."""

    content: str
    model: str
    tokens_used: int
    generation_time: float
    raw_response: Optional[dict] = None


@dataclass
class ValidationResult:
    """Result of content validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quality_score: float = 0.0


class PromptTemplateManager:
    """Manages prompt templates for different gap types."""

    def __init__(self):
        self._templates = {
            GapTypePrompt.DEFINITION.value: self._definition_template,
            GapTypePrompt.COMPARISON.value: self._comparison_template,
            GapTypePrompt.UPDATE.value: self._update_template,
            GapTypePrompt.EXAMPLE.value: self._example_template,
            GapTypePrompt.EXPLANATION.value: self._explanation_template,
            GapTypePrompt.EXPANSION.value: self._expansion_template,
            GapTypePrompt.PREREQUISITES.value: self._prerequisites_template,
        }

    def get_prompt(self, gap_type: str, request: EnrichmentRequest) -> str:
        """Get formatted prompt for the gap type."""
        template_fn = self._templates.get(gap_type, self._default_template)
        return template_fn(request)

    def _definition_template(self, request: EnrichmentRequest) -> str:
        return f"""You are a knowledge base assistant. Generate a clear, comprehensive definition for the following topic.

Topic: {request.topic}
Context: {request.query_context}

Existing sources consulted:
{chr(10).join(f"- {s}" for s in request.existing_sources) if request.existing_sources else "None"}

Generate a markdown section with:
1. Clear definition (2-3 sentences)
2. Key concepts (bullet list)
3. Related terms (if applicable)
4. Brief example (if helpful)

Output format: Clean markdown only, no explanations."""

    def _comparison_template(self, request: EnrichmentRequest) -> str:
        return f"""You are a knowledge base assistant. Generate a detailed comparison for the following topic.

Topic: {request.topic}
Context: {request.query_context}

Existing sources consulted:
{chr(10).join(f"- {s}" for s in request.existing_sources) if request.existing_sources else "None"}

Generate a markdown section with:
1. Comparison table (if applicable)
2. Key differences (bullet list)
3. Use cases for each option
4. Summary recommendation

Output format: Clean markdown only, no explanations."""

    def _update_template(self, request: EnrichmentRequest) -> str:
        return f"""You are a knowledge base assistant. Generate updated information for the following topic.

Topic: {request.topic}
Context: {request.query_context}

Existing sources consulted:
{chr(10).join(f"- {s}" for s in request.existing_sources) if request.existing_sources else "None"}

Generate a markdown section with:
1. Current state/versions
2. Recent changes or updates
3. Migration notes (if applicable)
4. Deprecation warnings (if applicable)

Output format: Clean markdown only, no explanations."""

    def _example_template(self, request: EnrichmentRequest) -> str:
        return f"""You are a knowledge base assistant. Generate practical examples for the following topic.

Topic: {request.topic}
Context: {request.query_context}

Existing sources consulted:
{chr(10).join(f"- {s}" for s in request.existing_sources) if request.existing_sources else "None"}

Generate a markdown section with:
1. Basic example (code or step-by-step)
2. Advanced example (if applicable)
3. Common pitfalls to avoid
4. Best practices

Output format: Clean markdown only, no explanations. Use code blocks for code."""

    def _explanation_template(self, request: EnrichmentRequest) -> str:
        return f"""You are a knowledge base assistant. Generate a comprehensive explanation for the following topic.

Topic: {request.topic}
Context: {request.query_context}

Existing sources consulted:
{chr(10).join(f"- {s}" for s in request.existing_sources) if request.existing_sources else "None"}

Generate a markdown section with:
1. Overview (2-3 sentences)
2. How it works (detailed explanation)
3. Components or steps (if applicable)
4. Related concepts

Output format: Clean markdown only, no explanations."""

    def _expansion_template(self, request: EnrichmentRequest) -> str:
        return f"""You are a knowledge base assistant. Expand on the following topic with more detail.

Topic: {request.topic}
Context: {request.query_context}

Existing sources consulted:
{chr(10).join(f"- {s}" for s in request.existing_sources) if request.existing_sources else "None"}

Generate a markdown section with:
1. Additional context
2. Edge cases or variations
3. Common questions
4. Further reading suggestions

Output format: Clean markdown only, no explanations."""

    def _prerequisites_template(self, request: EnrichmentRequest) -> str:
        return f"""You are a knowledge base assistant. Generate prerequisite information for the following topic.

Topic: {request.topic}
Context: {request.query_context}

Existing sources consulted:
{chr(10).join(f"- {s}" for s in request.existing_sources) if request.existing_sources else "None"}

Generate a markdown section with:
1. Required background knowledge
2. Prerequisites to understand first
3. Links to related topics (use [[wikilink]] format)
4. Quick refreshers (if applicable)

Output format: Clean markdown only, no explanations."""

    def _default_template(self, request: EnrichmentRequest) -> str:
        return f"""You are a knowledge base assistant. Generate content to fill a knowledge gap.

Topic: {request.topic}
Context: {request.query_context}

Existing sources consulted:
{chr(10).join(f"- {s}" for s in request.existing_sources) if request.existing_sources else "None"}

Generate a comprehensive markdown section that addresses this topic thoroughly.

Output format: Clean markdown only, no explanations."""


class ResponseValidator:
    """Validates LLM responses for format and quality."""

    def __init__(self):
        self._min_length = 50
        self._max_length = 10000
        self._required_sections = {
            "definition": ["definition", "concepts"],
            "comparison": ["comparison", "differences"],
            "update": ["current", "changes"],
            "example": ["example", "code"],
            "explanation": ["overview", "how"],
            "expansion": ["additional", "context"],
            "prerequisites": ["required", "background"],
        }

    def validate(
        self, content: str, gap_type: str, request: EnrichmentRequest
    ) -> ValidationResult:
        """Validate LLM response content."""
        errors = []
        warnings = []
        quality_score = 1.0

        if not content or not content.strip():
            errors.append("Empty response content")
            return ValidationResult(is_valid=False, errors=errors, quality_score=0.0)

        content_lower = content.lower()
        length = len(content)

        if length < self._min_length:
            errors.append(
                f"Content too short: {length} chars (min: {self._min_length})"
            )
            quality_score -= 0.3
        elif length > self._max_length:
            warnings.append(
                f"Content too long: {length} chars (max: {self._max_length})"
            )
            quality_score -= 0.1

        required = self._required_sections.get(gap_type, [])
        for section in required:
            if section not in content_lower:
                warnings.append(f"Missing expected section: {section}")
                quality_score -= 0.1

        if "```" in content and not content.strip().startswith("```"):
            warnings.append("Code blocks should be properly formatted")

        if any(marker in content for marker in ["I cannot", "I'm sorry", "As an AI"]):
            warnings.append("Response contains refusal or limitation language")
            quality_score -= 0.2

        is_valid = len(errors) == 0 and quality_score >= 0.5

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            quality_score=max(0.0, quality_score),
        )


class EnrichmentClient:
    """
    Client for calling external LLM APIs to generate content for knowledge gaps.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "gpt-4o-mini",
        default_temperature: float = 0.7,
        timeout: int = 60,
    ):
        self.api_key = (
            api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        )
        self.base_url = base_url or os.getenv(
            "LLM_BASE_URL", "https://api.openai.com/v1"
        )
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.timeout = timeout

        self.template_manager = PromptTemplateManager()
        self.validator = ResponseValidator()

    def enrich(
        self,
        gap_type: str,
        topic: str,
        query_context: str,
        existing_sources: Optional[list[str]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 2000,
    ) -> tuple[EnrichmentResponse, ValidationResult]:
        """
        Call LLM to generate content for a knowledge gap.

        Args:
            gap_type: Type of gap (definition, comparison, example, etc.)
            topic: Main topic to generate content about
            query_context: Context from the original query
            existing_sources: Sources already consulted
            model: LLM model to use (defaults to self.default_model)
            temperature: Sampling temperature (defaults to self.default_temperature)
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (EnrichmentResponse, ValidationResult)
        """
        if not self.api_key:
            raise ValueError(
                "API key not configured. Set OPENAI_API_KEY or LLM_API_KEY"
            )

        request = EnrichmentRequest(
            gap_type=gap_type,
            topic=topic,
            query_context=query_context,
            existing_sources=existing_sources or [],
            model=model or self.default_model,
            temperature=temperature or self.default_temperature,
            max_tokens=max_tokens,
        )

        prompt = self.template_manager.get_prompt(gap_type, request)

        start_time = time.time()

        response = self._call_llm(prompt, request)
        generation_time = time.time() - start_time

        response.generation_time = generation_time

        validation = self.validator.validate(response.content, gap_type, request)

        return response, validation

    def _call_llm(self, prompt: str, request: EnrichmentRequest) -> EnrichmentResponse:
        """Make the actual LLM API call."""
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": request.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful knowledge base assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }

            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)

            return EnrichmentResponse(
                content=content,
                model=request.model,
                tokens_used=tokens_used,
                generation_time=0.0,
                raw_response=data,
            )

        except ImportError:
            return self._fallback_call(prompt, request)
        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {e}")

    def _fallback_call(
        self, prompt: str, request: EnrichmentRequest
    ) -> EnrichmentResponse:
        """Fallback when httpx is not available - uses openai library."""
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
            )

            response = client.chat.completions.create(
                model=request.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful knowledge base assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0

            return EnrichmentResponse(
                content=content,
                model=request.model,
                tokens_used=tokens_used,
                generation_time=0.0,
            )

        except ImportError:
            raise RuntimeError(
                "Neither httpx nor openai library available. "
                "Install with: pip install httpx openai"
            )

    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return bool(self.api_key)

    def get_available_models(self) -> list[str]:
        """Get list of available models."""
        return [m.value for m in EnrichmentModel]
