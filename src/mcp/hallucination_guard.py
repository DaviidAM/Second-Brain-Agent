"""
Hallucination Guard - Phase 5: AI Response Generation and Safety Controls
Validates claims against source material and detects ungrounded statements.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ClaimType(Enum):
    """Types of claims that can be validated."""

    FACTUAL = "factual"
    DEFINITIONAL = "definitional"
    COMPARATIVE = "comparative"
    PROCEDURAL = "procedural"
    STATISTICAL = "statistical"
    UNKNOWN = "unknown"


@dataclass
class Claim:
    """Represents a claim in the response."""

    text: str
    claim_type: ClaimType
    start_pos: int
    end_pos: int
    is_grounded: bool = False
    supporting_sources: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of claim validation."""

    claim: str
    is_valid: bool
    is_grounded: bool
    confidence: float
    warning: Optional[str] = None
    severity: str = "none"


@dataclass
class HallucinationReport:
    """Complete report on hallucination detection."""

    total_claims: int
    grounded_claims: int
    ungrounded_claims: int
    warnings: list[str] = field(default_factory=list)
    blocked: bool = False
    blocked_claims: list[str] = field(default_factory=list)


class ClaimValidator:
    """Validates individual claims against source material."""

    def __init__(self):
        self._claim_patterns = {
            ClaimType.FACTUAL: [
                r"\b(is|are|was|were)\s+\w+",
                r"\b(contains|includes|has|have)\s+\w+",
            ],
            ClaimType.DEFINITIONAL: [
                r"\b(is\s+(?:a|an|the)\s+)?\w+(?:\s+\w+){0,3}\s+that\s+",
                r"\brefers\s+to\b",
                r"\bdefined\s+as\b",
            ],
            ClaimType.COMPARATIVE: [
                r"\b(more|less|better|worse)\s+than\b",
                r"\bdifferent\s+from\b",
                r"\bsimilar\s+to\b",
            ],
            ClaimType.PROCEDURAL: [
                r"\b(first|then|next|finally)\b",
                r"\bsteps?\s+(to|for)\b",
                r"\bhow\s+to\b",
            ],
            ClaimType.STATISTICAL: [
                r"\b\d+(?:\.\d+)?%\b",
                r"\b(majority|minority|all|none)\b",
                r"\bstudy\s+shows\b",
            ],
        }

    def extract_claims(self, text: str) -> list[Claim]:
        """Extract claims from text."""
        sentences = re.split(r"[.!?]+", text)
        claims = []

        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 10:
                continue

            claim_type = self._classify_claim(sent)

            claims.append(
                Claim(
                    text=sent,
                    claim_type=claim_type,
                    start_pos=text.find(sent),
                    end_pos=text.find(sent) + len(sent),
                )
            )

        return claims

    def _classify_claim(self, text: str) -> ClaimType:
        """Classify the type of claim."""
        text_lower = text.lower()

        for claim_type, patterns in self._claim_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return claim_type

        return ClaimType.UNKNOWN

    def validate_claim(self, claim: Claim, sources: list[dict]) -> ValidationResult:
        """Validate a single claim against sources."""
        claim_lower = claim.text.lower()

        is_grounded = False
        supporting = []

        for source in sources:
            source_text = source.get("snippet", "").lower()
            source_path = source.get("path", "")

            claim_words = set(claim_lower.split())
            source_words = set(source_text.split())

            overlap = claim_words & source_words
            if len(overlap) >= 3:
                is_grounded = True
                supporting.append(source_path)

            if any(word in source_text for word in ["not", "no", "never", "none"]):
                if any(neg in claim_lower for neg in ["not", "no", "never", "none"]):
                    is_grounded = True
                    supporting.append(source_path)

        confidence = len(supporting) / max(len(sources), 1)

        if claim.claim_type == ClaimType.STATISTICAL:
            if not re.search(r"\d+%|\d+\s+percent", claim.text):
                confidence *= 0.8

        return ValidationResult(
            claim=claim.text,
            is_valid=True,
            is_grounded=is_grounded,
            confidence=confidence,
            severity="high" if not is_grounded and confidence < 0.3 else "none",
        )


class UncertaintyHandler:
    """Handles uncertainty in responses."""

    def __init__(self):
        self._uncertainty_markers = {
            "high": ["might", "may", "could be", "possibly", "perhaps"],
            "medium": ["likely", "probably", "seems", "appears"],
            "low": ["suggests", "indicates", "appears to"],
        }

    def inject_uncertainty(
        self, text: str, confidence: float, claim_validations: list[ValidationResult]
    ) -> str:
        """Inject uncertainty markers where needed."""
        if confidence >= 0.8:
            return text

        ungrounded = [v for v in claim_validations if not v.is_grounded]

        if not ungrounded:
            return text

        if confidence < 0.5:
            prefix = "Based on limited information: "
            return prefix + text

        if confidence < 0.7:
            for marker in self._uncertainty_markers["medium"]:
                if marker not in text.lower():
                    text = text.replace(".", f" It seems {marker}.")
                    break

        return text

    def format_uncertain_response(self, text: str, gaps: list[dict]) -> str:
        """Format response with explicit uncertainty."""
        if not gaps:
            return text

        gap_note = "\n\n**Note**: This answer may be incomplete because:\n"

        for gap in gaps[:3]:
            topic = gap.get("topic", "")
            gap_note += f"- Missing information about: {topic}\n"

        return text + gap_note

    def should_block(
        self,
        confidence: float,
        claim_validations: list[ValidationResult],
        high_risk_domains: list[str] = None,
    ) -> tuple[bool, str]:
        """Determine if response should be blocked."""
        high_risk_domains = high_risk_domains or []

        if confidence < 0.3:
            ungrounded = sum(1 for v in claim_validations if not v.is_grounded)
            if ungrounded > 2:
                return True, "Too many ungrounded claims with very low confidence"

        for validation in claim_validations:
            if validation.severity == "high" and not validation.is_grounded:
                domain_keywords = {
                    "medical": ["treatment", "diagnosis", "medication", "doctor"],
                    "legal": ["law", "legal", "court", "rights", "liable"],
                    "financial": ["investment", "financial", "money", "cost"],
                }

                for domain, keywords in domain_keywords.items():
                    if domain in high_risk_domains:
                        if any(k in validation.claim.lower() for k in keywords):
                            return True, f"High-risk unverified claim in {domain}"

        return False, ""


class HallucinationGuard:
    """
    Main guard class for detecting and preventing hallucinations.
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        block_on_low_confidence: bool = True,
        high_risk_domains: Optional[list[str]] = None,
    ):
        self.claim_validator = ClaimValidator()
        self.uncertainty_handler = UncertaintyHandler()
        self.min_confidence = min_confidence
        self.block_on_low_confidence = block_on_low_confidence
        self.high_risk_domains = high_risk_domains or []

    def validate_response(
        self,
        response: str,
        sources: list[dict],
        confidence: float,
        gaps: Optional[list[dict]] = None,
    ) -> HallucinationReport:
        """
        Validate response for hallucinations.

        Args:
            response: Generated response text
            sources: Source documents used
            confidence: Overall confidence score
            gaps: Optional gap information

        Returns:
            HallucinationReport with validation results
        """
        claims = self.claim_validator.extract_claims(response)

        if not claims:
            return HallucinationReport(
                total_claims=0, grounded_claims=0, ungrounded_claims=0
            )

        validations = []
        for claim in claims:
            validation = self.claim_validator.validate_claim(claim, sources)
            validations.append(validation)

        grounded = sum(1 for v in validations if v.is_grounded)
        ungrounded = sum(1 for v in validations if not v.is_grounded)

        warnings = []
        for v in validations:
            if not v.is_grounded and v.confidence < 0.5:
                warnings.append(f"Ungrounded claim: {v.claim[:50]}...")

        blocked = False
        blocked_claims = []

        should_block, reason = self.uncertainty_handler.should_block(
            confidence, validations, self.high_risk_domains
        )

        if should_block and self.block_on_low_confidence:
            blocked = True
            blocked_claims = [v.claim for v in validations if not v.is_grounded]
            warnings.append(f"Response blocked: {reason}")

        return HallucinationReport(
            total_claims=len(claims),
            grounded_claims=grounded,
            ungrounded_claims=ungrounded,
            warnings=warnings,
            blocked=blocked,
            blocked_claims=blocked_claims,
        )

    def guard_response(
        self,
        response: str,
        sources: list[dict],
        confidence: float,
        gaps: Optional[list[dict]] = None,
    ) -> tuple[str, HallucinationReport]:
        """
        Apply guards to response and return modified response.

        Returns:
            Tuple of (guarded_response, report)
        """
        report = self.validate_response(response, sources, confidence, gaps)

        if report.blocked:
            return "", report

        if confidence < 0.7:
            claims = self.claim_validator.extract_claims(response)
            validations = [
                self.claim_validator.validate_claim(c, sources) for c in claims
            ]

            response = self.uncertainty_handler.inject_uncertainty(
                response, confidence, validations
            )

        if gaps:
            response = self.uncertainty_handler.format_uncertain_response(
                response, gaps
            )

        return response, report

    def check_claim_grounding(self, claim: str, sources: list[dict]) -> bool:
        """Quick check if a single claim is grounded."""
        claim_obj = Claim(
            text=claim, claim_type=ClaimType.UNKNOWN, start_pos=0, end_pos=len(claim)
        )

        validation = self.claim_validator.validate_claim(claim_obj, sources)
        return validation.is_grounded
