"""Conservative, deterministic checks for directly comparable document values.

This module is not an AI provider and does not make legal conclusions. A match
only flags source passages with different numeric payment deadlines for review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_PAYMENT_CONTEXT = re.compile(r"\b(payment|payable|invoice|settlement)\b", re.IGNORECASE)
_DURATION = re.compile(
    r"\b(?:within|in|after|no later than)\s+(\d{1,4})\s+(business\s+)?days?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PaymentTerm:
    section_id: str
    page_number: int
    text: str
    amount: int
    unit: str


@dataclass(frozen=True)
class PaymentTermConflict:
    terms: tuple[PaymentTerm, ...]


def find_payment_term_conflict(sections: list[dict[str, Any]]) -> PaymentTermConflict | None:
    """Return conflicting payment deadlines only when the source text states them.

    The detector requires an explicit payment-related word in the same sentence
    as each numeric deadline. It returns no finding when it cannot safely pair
    two distinct source passages.
    """
    terms: list[PaymentTerm] = []
    for section in sections:
        content = section.get("content")
        if not isinstance(content, str):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", content):
            if not _PAYMENT_CONTEXT.search(sentence):
                continue
            for match in _DURATION.finditer(sentence):
                terms.append(PaymentTerm(
                    section_id=str(section.get("id", "")),
                    page_number=int(section.get("page_number", 0)),
                    text=sentence.strip(),
                    amount=int(match.group(1)),
                    unit="business days" if match.group(2) else "days",
                ))

    distinct = {(term.amount, term.unit) for term in terms}
    if len(distinct) < 2:
        return None
    selected: list[PaymentTerm] = []
    seen: set[tuple[str, int, str]] = set()
    for term in terms:
        key = (term.section_id, term.amount, term.unit)
        if key not in seen:
            selected.append(term)
            seen.add(key)
    if not any(term.section_id for term in selected):
        return None
    return PaymentTermConflict(tuple(selected))


def describe_payment_term_conflict(conflict: PaymentTermConflict) -> tuple[str, str, list[str]]:
    labels = sorted({f"{term.amount} {term.unit}" for term in conflict.terms})
    summary = "Deterministic check: differing payment deadlines (" + " and ".join(labels) + ")."
    explanation = (
        "The extracted document contains different numeric payment deadlines in payment-related sentences. "
        "This rule-based check cannot determine whether the terms govern the same obligation; review their "
        "clauses, definitions, exceptions, amendments, schedules, and applicable document version."
    )
    uncertainty = [
        "DETERMINISTIC CHECK — NOT AI ANALYSIS. Different values may apply to separate obligations or versions.",
        "Human review is required before treating these passages as inconsistent.",
    ]
    return summary, explanation, uncertainty
