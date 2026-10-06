import re
from collections.abc import Iterable
from typing import Any

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "were",
    "will", "with", "shall", "under",
}


def terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w]+", text.casefold())
        if len(token) > 1 and token not in STOP_WORDS
    }


def rank_sections(
    query: str, sections: Iterable[dict[str, Any]], limit: int = 5
) -> list[dict[str, Any]]:
    """Small lexical retriever. It returns source rows, never unreferenced text."""
    query_terms = terms(query)
    if not query_terms:
        return []
    ranked: list[tuple[float, dict[str, Any]]] = []
    for section in sections:
        content = str(section.get("content", ""))
        content_terms = terms(content)
        overlap = len(query_terms & content_terms)
        if not overlap:
            continue
        score = overlap / (len(query_terms) ** 0.5 * max(1, len(content_terms)) ** 0.5)
        ranked.append((score, section))
    ranked.sort(key=lambda item: (item[0], -int(item[1].get("page_number", 1))), reverse=True)
    return [row for _, row in ranked[:limit]]
