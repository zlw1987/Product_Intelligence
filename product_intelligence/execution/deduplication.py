"""Candidate URL deduplication for execution.

Deterministic first-occurrence-wins exact URL deduplication.
"""

from __future__ import annotations


class CandidateDeduplicator:
    """Track candidate URLs to avoid fetching duplicates.

    Deterministic first-occurrence-wins exact URL deduplication.
    This matters for:
    * Avoiding unnecessary fetch work
    * Preventing the same page from contributing duplicate listing evidence
    """

    def __init__(self) -> None:
        self._seen_urls: set[str] = set()

    def is_duplicate(self, url: str) -> bool:
        """Check if URL has already been seen.

        Returns True if this URL has been seen before, False otherwise.
        If False, the URL is added to the seen set for future calls.
        """
        if not url:
            return False
        normalized = url.strip()
        if normalized in self._seen_urls:
            return True
        self._seen_urls.add(normalized)
        return False
