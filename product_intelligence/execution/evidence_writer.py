"""Execution evidence persistence service.

This module provides a strict API for recording execution attempts during
orchestration. It validates inputs and assigns contiguous attempt numbers.

PRODUCT-INTEL.4C-B corrections:
* Uses ExecutionDetailCode enum directly from domain.evidence
* Attempt number increment happens ONLY after successful DB INSERT
* candidate_url is NOT truncated (TextField, preserve provenance)
* Validates stage/outcome/detail combinations are legal
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlsplit

from product_intelligence.domain.evidence import (
    ExecutionDetailCode,
    ExecutionOutcome,
    ExecutionStage,
)
from product_intelligence.runs.models import ExecutionEvidenceRecord

if TYPE_CHECKING:
    from product_intelligence.runs.models import ResearchRun

logger = logging.getLogger(__name__)


class ExecutionEvidenceCorruptionError(Exception):
    """Raised when evidence data is corrupt or invalid.

    This is raised by the evidence reader when it encounters:
    * Non-contiguous attempt numbers
    * Unknown stage/outcome/detail codes
    * Malformed URLs
    * Impossible stage/outcome/detail combinations
    """

    pass


def _is_safe_absolute_url(value: str | None) -> bool:
    """Validate a URL for safe persistence.

    Rules:
    * Must be absolute http(s)://
    * Must have a non-empty hostname
    * Must not contain credentials (username/password in URL)
    * Must not be None or empty

    This is a pure validation function that returns False for any issue,
    never raises. Safe URLs can be persisted; unsafe ones should use empty string.
    """
    if not value:
        return False

    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"}:
            return False
        if not parts.hostname:
            return False
        # Check for embedded credentials
        if parts.username is not None or parts.password is not None:
            return False
        return True
    except Exception:
        return False


def _validate_url_strict(value: str) -> bool:
    """Strict URL validation - returns True if valid, raises ValueError if invalid.
    
    This is used by the reader to validate persisted URLs.
    
    Rules:
    * Must be http(s)://
    * Must have non-empty hostname
    * Must not contain credentials
    
    Raises ValueError for invalid URLs instead of returning False.
    """
    if not value:
        return False
    
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"}:
            raise ValueError(f"URL must be http(s)://, got {parts.scheme!r}")
        if not parts.hostname:
            raise ValueError(f"URL must have a hostname, got {value!r}")
        if parts.username is not None or parts.password is not None:
            raise ValueError(f"URL must not contain credentials")
        return True
    except Exception as exc:
        raise ValueError(f"Malformed URL {value!r}: {exc}") from exc


def _has_credentials(value: str | None) -> bool:
    """Check if a URL contains embedded credentials."""
    if not value:
        return False
    try:
        parts = urlsplit(value)
        return parts.username is not None or parts.password is not None
    except Exception:
        return False


def _validate_combination_shared(
    stage: ExecutionStage,
    outcome: ExecutionOutcome,
    detail_code: ExecutionDetailCode | None,
) -> None:
    """Shared combination validator used by both writer and reader.
    
    Raises ValueError for impossible combinations.
    """
    key = (stage, outcome)
    if key not in _VALID_COMBINATIONS:
        raise ValueError(
            f"Invalid stage/outcome combination: {stage.value}/{outcome.value}"
        )
    allowed = _VALID_COMBINATIONS[key]
    if detail_code not in allowed:
        raise ValueError(
            f"Invalid detail_code {detail_code} for {stage.value}/{outcome.value}. "
            f"Allowed: {sorted(str(d) for d in allowed if d)}"
        )


# Valid stage/outcome/detail combinations
# This is the authoritative mapping per PRODUCT-INTEL.4C-B requirements
# Each entry maps (stage, outcome) -> set of allowed detail codes or None
_VALID_COMBINATIONS: dict[tuple[ExecutionStage, ExecutionOutcome], set[ExecutionDetailCode | None]] = {
    # SEARCH
    (ExecutionStage.SEARCH, ExecutionOutcome.SUCCESS): {
        ExecutionDetailCode.OK,
        ExecutionDetailCode.ZERO_RESULTS,
    },
    (ExecutionStage.SEARCH, ExecutionOutcome.FAILED): {
        ExecutionDetailCode.PROVIDER_ERROR,
        ExecutionDetailCode.TIMEOUT,
    },
    # FETCH
    (ExecutionStage.FETCH, ExecutionOutcome.SUCCESS): {
        ExecutionDetailCode.OK,
    },
    (ExecutionStage.FETCH, ExecutionOutcome.BLOCKED): {
        ExecutionDetailCode.SAFE_URL_REFUSED,
    },
    (ExecutionStage.FETCH, ExecutionOutcome.FAILED): {
        ExecutionDetailCode.NETWORK_ERROR,
        ExecutionDetailCode.HTTP_ERROR,
        ExecutionDetailCode.TIMEOUT,
    },
    (ExecutionStage.FETCH, ExecutionOutcome.SKIPPED): {
        None,  # Duplicate - no detail code
    },
    # EXTRACT
    (ExecutionStage.EXTRACT, ExecutionOutcome.SUCCESS): {
        ExecutionDetailCode.OK,
    },
    (ExecutionStage.EXTRACT, ExecutionOutcome.EMPTY): {
        ExecutionDetailCode.NO_LISTING_OBSERVATIONS,
    },
    (ExecutionStage.EXTRACT, ExecutionOutcome.FAILED): {
        ExecutionDetailCode.PARSE_ERROR,
    },
    # NORMALIZE
    (ExecutionStage.NORMALIZE, ExecutionOutcome.SUCCESS): {
        ExecutionDetailCode.OK,
        ExecutionDetailCode.NO_PRICE,
    },
    (ExecutionStage.NORMALIZE, ExecutionOutcome.FAILED): {
        None,  # Primitive failure - no detail code
    },
    # MATCH
    (ExecutionStage.MATCH, ExecutionOutcome.SUCCESS): {
        ExecutionDetailCode.ACCEPTED,
        ExecutionDetailCode.IDENTITY_REJECTED,
        ExecutionDetailCode.NO_MPN_IN_OBSERVATION,
        None,  # UNDECIDED or description-only - no detail code
    },
    (ExecutionStage.MATCH, ExecutionOutcome.FAILED): {
        None,  # Primitive failure - no detail code
    },
    # AGGREGATE
    (ExecutionStage.AGGREGATE, ExecutionOutcome.SUCCESS): {
        None,  # SUCCESS has no additional detail
    },
    (ExecutionStage.AGGREGATE, ExecutionOutcome.FAILED): {
        None,  # Primitive failure - no detail code
    },
}


class ExecutionEvidenceWriter:
    """Strict execution evidence write service.

    This service provides a single supported path for recording execution
    attempts during orchestration. It:

    * Validates stage/outcome/detail_code against controlled vocabulary
    * Validates candidate_url rules (no credentials, absolute URL or empty)
    * Assigns contiguous attempt numbers starting at 1
    * Persists exactly one row per call
    * Returns the domain representation for auditability

    The orchestrator must NOT scatter direct ExecutionEvidenceRecord.objects.create()
    calls throughout orchestration.

    Attempt number assignment (CRITICAL):
        attempt_number = self._next_attempt_number
        record = ExecutionEvidenceRecord.objects.create(...)
        self._next_attempt_number += 1

    The increment happens ONLY after successful persistence.
    """

    def __init__(self, run: ResearchRun):
        self._run = run
        self._next_attempt_number = 1

    def _validate_combination(
        self,
        stage: ExecutionStage,
        outcome: ExecutionOutcome,
        detail_code: ExecutionDetailCode | None,
    ) -> None:
        """Validate stage/outcome/detail combination is legal.
        
        This validator is shared by both writer and reader to ensure consistency.
        An impossible combination raises ValueError which propagates as
        execution-level catastrophic failure.
        """
        key = (stage, outcome)
        if key not in _VALID_COMBINATIONS:
            raise ValueError(
                f"Invalid stage/outcome combination: {stage.value}/{outcome.value}"
            )
        allowed = _VALID_COMBINATIONS[key]
        if detail_code not in allowed:
            raise ValueError(
                f"Invalid detail_code {detail_code} for {stage.value}/{outcome.value}. "
                f"Allowed: {sorted(str(d) for d in allowed if d)}"
            )

    def _validate_url(self, candidate_url: str) -> str:
        """Validate URL for safe persistence.
        
        Returns the URL to persist. 
        
        Rules:
        * Empty string is valid (no URL available)
        * Valid http(s):// with non-empty hostname
        * If URL has credentials, return empty string (caller handles this)
        * If URL is malformed (not http(s)://, no hostname, etc.), raise ValueError
        
        Raises ValueError for malformed URLs - this is a programming error.
        Returns empty string for credential-bearing URLs - caller should handle this
        by passing empty string in the first place.
        """
        # Empty URL is valid where caller has no safe URL to persist
        if not candidate_url:
            return candidate_url
        
        try:
            parts = urlsplit(candidate_url)
            
            # Must be http or https
            if parts.scheme.lower() not in {"http", "https"}:
                raise ValueError(
                    f"URL must be http(s)://, got {parts.scheme!r}"
                )
            
            # Must have a non-empty hostname
            if not parts.hostname:
                raise ValueError(
                    f"URL must have a hostname, got {candidate_url!r}"
                )
            
            # Check for embedded credentials - this is a programming error
            # Orchestration should pass empty string "" for credential URLs it handles
            if parts.username is not None or parts.password is not None:
                raise ValueError(
                    f"URL must not contain credentials; "
                    f"pass candidate_url=\"\" for handled credential URLs"
                )
            
            # Valid URL - return as-is
            return candidate_url
            
        except ValueError:
            # Re-raise ValueError for malformed URLs
            raise
        except Exception as exc:
            # Other exceptions during parsing are malformed URLs
            raise ValueError(
                f"Malformed URL {candidate_url!r}: {exc}"
            ) from exc

    def append_execution_attempt(
        self,
        stage: ExecutionStage,
        outcome: ExecutionOutcome,
        candidate_url: str = "",
        detail_code: ExecutionDetailCode | None = None,
    ) -> ExecutionEvidenceRecord:
        """Record one execution attempt.

        Parameters
        ----------
        stage : ExecutionStage
            The research primitive being called (SEARCH, FETCH, EXTRACT, etc.)
        outcome : ExecutionOutcome
            The result (SUCCESS, FAILED, SKIPPED, BLOCKED, EMPTY)
        candidate_url : str, optional
            The URL operated on, if applicable. Empty string for SEARCH.
            If the URL contains credentials, pass empty string "" instead.
        detail_code : ExecutionDetailCode | None, optional
            Stable machine-readable code explaining outcome.
            None means "no additional detail" which is valid for some outcomes.

        Returns
        -------
        ExecutionEvidenceRecord
            The persisted record for auditability.

        Raises
        ------
        TypeError, ValueError
            If any parameter fails validation.
        ExecutionEvidenceCorruptionError (never from writer, only reader)
        """
        # Validate stage/outcome
        if not isinstance(stage, ExecutionStage):
            raise TypeError(f"stage must be an ExecutionStage, got {type(stage).__name__}")
        if not isinstance(outcome, ExecutionOutcome):
            raise TypeError(f"outcome must be an ExecutionOutcome, got {type(outcome).__name__}")

        # Validate detail_code type
        if detail_code is not None and not isinstance(detail_code, ExecutionDetailCode):
            raise TypeError(
                f"detail_code must be ExecutionDetailCode or None, got {type(detail_code).__name__}"
            )

        # Validate the combination is legal
        self._validate_combination(stage, outcome, detail_code)

        # Validate candidate_url - may raise ValueError for malformed URLs
        # or return empty string for credential-bearing URLs
        try:
            validated_url = self._validate_url(candidate_url)
        except ValueError as exc:
            # Malformed URL - this is a programming error, not recoverable
            raise ValueError(
                f"Invalid candidate_url for evidence write: {exc}"
            ) from exc

        # Get attempt number BEFORE creating record
        attempt_number = self._next_attempt_number

        # Persist the record
        try:
            record = ExecutionEvidenceRecord.objects.create(
                run=self._run,
                attempt_number=attempt_number,
                stage=stage.value,
                outcome=outcome.value,
                candidate_url=validated_url,
                detail_code=detail_code.value if detail_code else "",
                created_at=datetime.now(tz=timezone.utc),
            )
        except Exception as exc:
            # Evidence write failure is execution-level catastrophic
            # Do not convert to a stage-specific error code
            logger.error(
                "Evidence write failed for run %s: %s", self._run.id, exc, exc_info=True
            )
            raise

        # Increment attempt number ONLY after successful persistence
        self._next_attempt_number += 1

        logger.debug(
            "Execution evidence recorded: run=%s attempt=%d stage=%s outcome=%s detail=%s",
            self._run.id,
            attempt_number,
            stage.value,
            outcome.value,
            detail_code.value if detail_code else "",
        )

        return record


def read_execution_evidence(run: ResearchRun) -> list[ExecutionEvidenceRecord]:
    """Read execution evidence for a run, failing closed on corruption.

    This is the STRICT reader that validates:
    * Attempt numbers are contiguous (1, 2, 3, ...)
    * Stage values are known ExecutionStage members
    * Outcome values are known ExecutionOutcome members
    * Detail codes are known ExecutionDetailCode members (or empty)
    * Candidate URLs are empty or safe absolute http(s) URLs
    * Stage/outcome/detail combinations are legal

    Returns
    -------
    list[ExecutionEvidenceRecord]
        Evidence records in attempt_number order.

    Raises
    ------
    ExecutionEvidenceCorruptionError
        If any evidence is corrupt or violates invariants.
    """
    records = list(
        ExecutionEvidenceRecord.objects.filter(run=run).order_by("attempt_number")
    )

    if not records:
        return []

    # Check attempt numbers are exactly 1..N
    attempt_numbers = [r.attempt_number for r in records]
    expected = list(range(1, len(records) + 1))
    if attempt_numbers != expected:
        raise ExecutionEvidenceCorruptionError(
            f"Non-contiguous attempt numbers: found {attempt_numbers}, expected {expected}"
        )

    # Validate each record
    for record in records:
        # Stage must be a known value
        try:
            stage = ExecutionStage(record.stage)
        except ValueError:
            raise ExecutionEvidenceCorruptionError(
                f"Unknown stage: {record.stage!r} at attempt {record.attempt_number}"
            )

        # Outcome must be a known value
        try:
            outcome = ExecutionOutcome(record.outcome)
        except ValueError:
            raise ExecutionEvidenceCorruptionError(
                f"Unknown outcome: {record.outcome!r} at attempt {record.attempt_number}"
            )

        # Detail code must be empty or known
        detail_code_str = record.detail_code
        detail_code: ExecutionDetailCode | None = None
        if detail_code_str:
            try:
                detail_code = ExecutionDetailCode(detail_code_str)
            except ValueError:
                raise ExecutionEvidenceCorruptionError(
                    f"Unknown detail_code: {detail_code_str!r} at attempt {record.attempt_number}"
                )

        # Candidate URL must be empty or a safe absolute URL
        if record.candidate_url:
            # Re-use the URL validation from writer
            try:
                validated = _validate_url_strict(record.candidate_url)
                if not validated:
                    raise ExecutionEvidenceCorruptionError(
                        f"Malformed/unsafe candidate_url: {record.candidate_url!r} at attempt {record.attempt_number}"
                    )
            except ValueError as exc:
                raise ExecutionEvidenceCorruptionError(
                    f"Malformed/unsafe candidate_url: {exc} at attempt {record.attempt_number}"
                ) from exc

        # Stage/outcome/detail combination must be legal - use writer's validator
        key = (stage, outcome)
        try:
            # Re-use writer's combination validation
            _validate_combination_shared(stage, outcome, detail_code)
        except ValueError as exc:
            raise ExecutionEvidenceCorruptionError(
                f"Invalid combination at attempt {record.attempt_number}: {exc}"
            ) from exc

    return records