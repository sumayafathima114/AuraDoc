from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RelationType(StrEnum):
    CONSISTENT = "CONSISTENT"
    POSSIBLE_DISCREPANCY = "POSSIBLE_DISCREPANCY"
    CONDITIONAL = "CONDITIONAL"
    TEMPORAL_VERSION_MISMATCH = "TEMPORAL_VERSION_MISMATCH"
    DEFINITION_EXCEPTION_MISMATCH = "DEFINITION_EXCEPTION_MISMATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class EvidenceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str
    document_name: str
    version_label: str
    page_number: int = Field(gt=0)
    section_label: str | None = None
    clause_label: str | None = None
    content: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class ComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relation: RelationType
    summary: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=4000)
    supporting_section_ids: list[str] = Field(default_factory=list, max_length=8)
    uncertainties: list[str] = Field(default_factory=list, max_length=20)
    requires_human_review: Literal[True]


class DocumentReviewResult(BaseModel):
    """Conservative document-only review; never represents a statement comparison."""
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=4000)
    supporting_section_ids: list[str] = Field(min_length=1, max_length=8)
    uncertainties: list[str] = Field(default_factory=list, max_length=20)
    requires_human_review: Literal[True]


class ComparisonEnvelope(BaseModel):
    assessment: ComparisonResult
    provider: str
    model_name: str
    prompt_version: str


class RecommendationPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class LegalSourceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    title: str = Field(min_length=1, max_length=500)
    source_type: str
    jurisdiction: str
    authority: str
    act_or_regulation: str | None = None
    section: str | None = None
    subsection: str | None = None
    publication_date: str | None = None
    effective_date: str | None = None
    version_label: str | None = None
    official_source_url: str
    source_text: str = Field(min_length=1, max_length=100_000)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class LegalRelevance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legal_source_id: UUID
    why_may_matter: str = Field(min_length=1, max_length=1500)
    evidence_connection: str = Field(min_length=1, max_length=1500)
    limitations: str = Field(min_length=1, max_length=1500)


class RecommendationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=2000)
    evidence_basis: str = Field(min_length=1, max_length=2000)
    priority: RecommendationPriority
    legal_source_id: UUID | None = None


class LegalAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legal_relevance: list[LegalRelevance] = Field(default_factory=list, max_length=10)
    missing_evidence: list[str] = Field(default_factory=list, max_length=20)
    recommendations: list[RecommendationDraft] = Field(default_factory=list, max_length=20)
    requires_human_review: Literal[True]
