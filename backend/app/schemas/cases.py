from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.analysis import RelationType


class CaseStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REVIEW = "REVIEW"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)

    @field_validator("title")
    @classmethod
    def title_must_contain_non_whitespace(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Case title cannot be blank.")
        return normalized


class DocumentMetadata(BaseModel):
    document_id: UUID
    version_id: UUID
    name: str
    version_label: str
    sha256_hash: str
    page_count: int
    section_count: int


class RecordingMetadata(BaseModel):
    recording_id: UUID
    sha256_hash: str
    duration_ms: int
    segment_count: int
    asr_provider: str
    asr_model: str


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript_segment_id: UUID
    document_version_id: UUID


class DocumentReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    focus_question: str | None = Field(default=None, max_length=500)


class ReviewDecision(StrEnum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    NEEDS_MORE_REVIEW = "NEEDS_MORE_REVIEW"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"
    MARK_RESOLVED = "MARK_RESOLVED"
    ESCALATE = "ESCALATE"


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    comment: str | None = Field(default=None, max_length=5000)


class HumanConclusionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lawyer_recommendation: str = Field(default="", max_length=10000)
    human_conclusion: str = Field(min_length=20, max_length=20000)
    limitations: str = Field(default="", max_length=10000)

    @field_validator("human_conclusion")
    @classmethod
    def conclusion_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 20:
            raise ValueError("Add a human conclusion of at least 20 characters.")
        return normalized


class LegalSourceType(StrEnum):
    ACT = "ACT"
    SECTION = "SECTION"
    RULE = "RULE"
    REGULATION = "REGULATION"
    NOTIFICATION = "NOTIFICATION"
    ORDER = "ORDER"
    JUDGMENT = "JUDGMENT"
    OTHER = "OTHER"


class LegalSourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=500)
    source_type: LegalSourceType
    jurisdiction: str = Field(default="INDIA", min_length=1, max_length=120)
    authority: str = Field(min_length=1, max_length=300)
    act_or_regulation: str | None = Field(default=None, max_length=500)
    section: str | None = Field(default=None, max_length=120)
    subsection: str | None = Field(default=None, max_length=120)
    publication_date: date | None = None
    effective_date: date | None = None
    version_label: str | None = Field(default=None, max_length=300)
    official_source_url: str = Field(min_length=1, max_length=2000)
    source_text: str = Field(min_length=1, max_length=100_000)

    @field_validator("title", "authority")
    @classmethod
    def trim_required(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("This field cannot be blank.")
        return result

    @field_validator("source_text")
    @classmethod
    def source_text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Source text cannot be blank.")
        return value


class LegalSourceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verification_status: str
    verification_notes: str = Field(min_length=20, max_length=5000)
    attest_official_source_checked: bool

    @field_validator("verification_status")
    @classmethod
    def allowed_state(cls, value: str) -> str:
        if value not in {"VERIFIED_OFFICIAL", "REJECTED", "OUTDATED"}:
            raise ValueError("Unsupported legal-source review state.")
        return value

    @field_validator("verification_notes")
    @classmethod
    def review_note_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 20:
            raise ValueError("Add review notes explaining what was checked.")
        return normalized

    @field_validator("attest_official_source_checked")
    @classmethod
    def must_attest_when_verified(cls, value: bool, info):
        if info.data.get("verification_status") == "VERIFIED_OFFICIAL" and not value:
            raise ValueError("A reviewer must attest that the official source was checked.")
        return value


class RecommendationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str

    @field_validator("status")
    @classmethod
    def supported_state(cls, value: str) -> str:
        if value not in {"OPEN", "COMPLETED", "DISMISSED"}:
            raise ValueError("Status must be OPEN, COMPLETED, or DISMISSED.")
        return value
