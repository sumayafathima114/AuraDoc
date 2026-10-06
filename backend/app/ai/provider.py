from typing import Protocol

from app.schemas.analysis import ComparisonResult, EvidenceCandidate


class AIProvider(Protocol):
    provider_name: str
    model_name: str

    async def compare(
        self, statement: str, candidates: list[EvidenceCandidate]
    ) -> ComparisonResult: ...
