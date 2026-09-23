"""Execution tests for 4D-D v1 alias-authority acquisition.

``acquire_micron_alias_eligibility`` is the bounded execution-layer
acquisition: one reviewed family-catalog fetch through the existing
PageFetcher protocol, origin enforcement, fail-closed parsing, frozen-2A
matching, SSD category evidence, and the customer-defined relation.

Expected acquisition failures are bounded results; programming/invariant
errors propagate. NO_REQUESTED_MPN (absent MPN) and INVALID_LOOKUP_BASE
(non-empty but unusable MPN) are distinct states, both with zero fetches.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from product_intelligence.domain import ResearchRequest
from product_intelligence.domain.enums import IdentityMatchType
from product_intelligence.execution.micron_alias_authority import (
    acquire_micron_alias_eligibility,
)
from product_intelligence.providers.page import (
    FetchedPage,
    PageFetchError,
    PageFetchRequest,
    PageFetcher,
    UnsafeFetchTargetError,
)
from product_intelligence.research.micron_packaging_alias import (
    MICRON_7500_APPROVED_ORIGIN,
    MICRON_7500_CATEGORY,
    MICRON_7500_MANUFACTURER,
    MICRON_7500_POLICY_ID,
    MICRON_7500_REQUESTED_CATALOG_URL,
    MICRON_7500_SOURCE_NAME,
    MicronAliasEligibilityStatus,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "pages"
CATALOG_FIXTURE = FIXTURES / "micron_7500_part_catalog.json"
BASE = "MTFDKCC3T8TGP-1BK1DABYY"
BASER = f"{BASE}R"
BASET = f"{BASE}T"
FIXTURE_SHA256 = (
    "160d4fe97a5df5249e8f6404f6b005c0515fab4def1b4668fdaf87c727600743"
)
UTC = timezone.utc
FIXED_AT = datetime(2026, 9, 22, 23, 20, 25, tzinfo=UTC)


def _fetcher_returning(body: "str | None", *, final_url: str | None = None) -> MagicMock:
    """A PageFetcher-shaped fake returning one FetchedPage."""
    fetcher = MagicMock(spec=PageFetcher)
    if body is not None:
        fetched = FetchedPage(
            requested_url=MICRON_7500_REQUESTED_CATALOG_URL,
            final_url=final_url or MICRON_7500_REQUESTED_CATALOG_URL,
            retrieved_at=FIXED_AT,
            status_code=200,
            body_text=body,
            content_type="application/json;charset=utf-8",
            body_byte_count=len(body.encode("utf-8")),
            redirect_count=0,
            fetcher_id="test",
        )
        fetcher.fetch.return_value = fetched
    return fetcher


def _fixture_body() -> str:
    return CATALOG_FIXTURE.read_bytes().decode("utf-8")


def _catalog(rows: list[dict[str, Any]]) -> str:
    return json.dumps({"details": rows})


class TestEstablishedFromRealFixture:
    @pytest.mark.parametrize("mpn", [BASE, BASER, BASET])
    def test_established_for_all_three_request_forms(self, mpn: str) -> None:
        fetcher = _fetcher_returning(_fixture_body())
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=mpn, description="7500"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert result.manufacturer == MICRON_7500_MANUFACTURER
        assert result.category == MICRON_7500_CATEGORY
        assert result.matched_base_mpn == BASE
        assert result.policy_id == MICRON_7500_POLICY_ID
        assert result.body_sha256 == FIXTURE_SHA256
        assert result.fetched_final_url == MICRON_7500_REQUESTED_CATALOG_URL
        assert result.retrieved_at == FIXED_AT
        assert result.source_name == MICRON_7500_SOURCE_NAME
        assert result.requested_source_url == MICRON_7500_REQUESTED_CATALOG_URL

    def test_relation_excludes_the_requested_form(self) -> None:
        fetcher = _fetcher_returning(_fixture_body())
        for mpn, expected in (
            (BASE, (BASER, BASET)),
            (BASER, (BASE, BASET)),
            (BASET, (BASE, BASER)),
        ):
            result = acquire_micron_alias_eligibility(
                request=ResearchRequest(manufacturer_part_number=mpn, description="d"),
                page_fetcher=fetcher,
            )
            assert result.alias_relation is not None
            assert result.alias_relation.aliases == expected
            assert mpn not in result.alias_relation.aliases

    def test_exact_requested_base_yields_exact_match_evidence(self) -> None:
        fetcher = _fetcher_returning(_fixture_body())
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=BASE, description="d"),
            page_fetcher=fetcher,
        )
        assert result.part_number_match is not None
        assert result.part_number_match.match_type is IdentityMatchType.EXACT
        assert result.ssd_category_evidence is not None
        assert result.ssd_category_evidence.attr_id == "is-ssd"
        assert result.ssd_category_evidence.attr_value is True
        assert result.ssd_category_evidence.attr_name == "SSD"

    def test_one_catalog_fetch_per_acquisition(self) -> None:
        fetcher = _fetcher_returning(_fixture_body())
        acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
            page_fetcher=fetcher,
        )
        assert fetcher.fetch.call_count == 1
        argument = fetcher.fetch.call_args.args[0]
        assert isinstance(argument, PageFetchRequest)
        assert argument.url == MICRON_7500_REQUESTED_CATALOG_URL

    def test_redirect_staying_inside_origin_is_established(self) -> None:
        inside = (
            MICRON_7500_REQUESTED_CATALOG_URL + "?locale=en_US"
        )
        fetcher = _fetcher_returning(_fixture_body(), final_url=inside)
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert result.fetched_final_url == inside


class TestPreFetchAbstentions:
    def test_absent_mpn_is_no_requested_mpn_with_zero_fetches(self) -> None:
        fetcher = _fetcher_returning(_fixture_body())
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number="", description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.NO_REQUESTED_MPN
        assert result.lookup_base_candidate is None
        assert fetcher.fetch.call_count == 0
        assert result.requested_source_url is None
        assert result.body_sha256 is None

    @pytest.mark.parametrize("mpn", ["-R", "-T", "R", "T", "----"])
    def test_non_empty_unusable_mpn_is_invalid_lookup_base_with_zero_fetches(
        self, mpn: str
    ) -> None:
        fetcher = _fetcher_returning(_fixture_body())
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=mpn, description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.INVALID_LOOKUP_BASE
        assert result.lookup_base_candidate is None
        assert fetcher.fetch.call_count == 0
        assert result.requested_source_url is None
        assert result.body_sha256 is None
        # The two pre-fetch abstentions are distinct persisted states.
        assert result.status is not MicronAliasEligibilityStatus.NO_REQUESTED_MPN

    def test_lower_final_r_does_not_trigger_rule_and_fetches(self) -> None:
        fetcher = _fetcher_returning(_fixture_body())
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(
                manufacturer_part_number=f"{BASE}r", description="d"
            ),
            page_fetcher=fetcher,
        )
        # The lowercase r is content, not the customer suffix: the full MPN
        # is the candidate, matches no catalog row, and is bounded.
        assert result.status is MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH
        assert result.lookup_base_candidate == f"{BASE}r"
        assert fetcher.fetch.call_count == 1


class TestBoundedFetchFailures:
    def test_fetch_error_is_bounded(self) -> None:
        fetcher = MagicMock(spec=PageFetcher)
        fetcher.fetch.side_effect = PageFetchError("network down")
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.FETCH_FAILED
        assert result.requested_source_url == MICRON_7500_REQUESTED_CATALOG_URL
        assert result.fetched_final_url is None
        assert result.body_sha256 is None

    def test_source_refusal_is_bounded(self) -> None:
        fetcher = MagicMock(spec=PageFetcher)
        fetcher.fetch.side_effect = UnsafeFetchTargetError("refused")
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.SOURCE_REFUSED
        assert result.requested_source_url == MICRON_7500_REQUESTED_CATALOG_URL
        assert result.fetched_final_url is None

    def test_host_escape_is_bounded(self) -> None:
        fetcher = _fetcher_returning(
            _fixture_body(), final_url="https://evil.example/catalog.json"
        )
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.HOST_ESCAPED
        assert result.fetched_final_url == "https://evil.example/catalog.json"
        assert result.source_name is None
        assert result.body_sha256 is None
        assert result.matched_base_mpn is None

    def test_scheme_downgrade_escape_is_bounded(self) -> None:
        fetcher = _fetcher_returning(
            _fixture_body(),
            final_url=MICRON_7500_REQUESTED_CATALOG_URL.replace("https://", "http://"),
        )
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.HOST_ESCAPED

    def test_non_json_body_is_parse_failed(self) -> None:
        fetcher = _fetcher_returning("<html>not json</html>")
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.PARSE_FAILED
        assert result.body_sha256 == hashlib.sha256(
            b"<html>not json</html>"
        ).hexdigest()

    def test_no_catalog_row_matches(self) -> None:
        fetcher = _fetcher_returning(_fixture_body())
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(
                manufacturer_part_number="NOT-IN-CATALOG", description="d"
            ),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.NO_AUTHORITY_MATCH
        assert result.body_sha256 == FIXTURE_SHA256
        assert result.matched_base_mpn is None
        assert result.alias_relation is None

    def test_ambiguous_match_fails_closed(self) -> None:
        # Two source-published rows 2A-equivalent to the candidate
        # ("AB-1" and "ab 1" both normalize to "AB-1").
        rows = [
            {"part-number": "AB-1", "part-name": "one", "attr": []},
            {"part-number": "ab 1", "part-name": "two", "attr": []},
        ]
        fetcher = _fetcher_returning(_catalog(rows))
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number="AB-1", description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.AMBIGUOUS_AUTHORITY_MATCH

    def test_matched_row_without_ssd_evidence(self) -> None:
        rows = [
            {
                "part-number": "AB-1",
                "part-name": "one",
                "attr": [{"name": "Capacity", "id": "capacity", "value": "1GB"}],
            }
        ]
        fetcher = _fetcher_returning(_catalog(rows))
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number="AB-1", description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.CATEGORY_NOT_SSD

    def test_matched_row_with_false_ssd_flag(self) -> None:
        rows = [
            {
                "part-number": "AB-1",
                "part-name": "one",
                "attr": [{"name": "SSD", "id": "is-ssd", "value": False}],
            }
        ]
        fetcher = _fetcher_returning(_catalog(rows))
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number="AB-1", description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.CATEGORY_NOT_SSD

    def test_string_true_ssd_flag_is_not_ssd(self) -> None:
        rows = [
            {
                "part-number": "AB-1",
                "part-name": "one",
                "attr": [{"name": "SSD", "id": "is-ssd", "value": "true"}],
            }
        ]
        fetcher = _fetcher_returning(_catalog(rows))
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(manufacturer_part_number="AB-1", description="d"),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.CATEGORY_NOT_SSD

    def test_established_synthetic_catalog_row(self) -> None:
        rows = [
            {
                "part-number": "SYN-100",
                "part-name": "Synthetic",
                "attr": [{"name": "SSD", "id": "is-ssd", "value": True}],
            }
        ]
        fetcher = _fetcher_returning(_catalog(rows))
        result = acquire_micron_alias_eligibility(
            request=ResearchRequest(
                manufacturer_part_number="SYN-100T", description="d"
            ),
            page_fetcher=fetcher,
        )
        assert result.status is MicronAliasEligibilityStatus.ESTABLISHED
        assert result.matched_base_mpn == "SYN-100"
        assert result.alias_relation is not None
        assert result.alias_relation.aliases == ("SYN-100", "SYN-100R")


class TestProgrammingErrorsPropagate:
    def test_non_request_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            acquire_micron_alias_eligibility(
                request="NOT-A-REQUEST",  # type: ignore[arg-type]
                page_fetcher=_fetcher_returning(_fixture_body()),
            )

    def test_unexpected_fetcher_error_propagates(self) -> None:
        fetcher = MagicMock(spec=PageFetcher)
        fetcher.fetch.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError):
            acquire_micron_alias_eligibility(
                request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
                page_fetcher=fetcher,
            )


class TestDependencyContractDefects:
    """4D-D FU1: dependency/programming contract defects propagate.

    The bounded surface of the authority pipeline is exactly the expected
    provider classification: ``PageFetchError`` -> FETCH_FAILED and
    ``UnsafeFetchTargetError`` -> SOURCE_REFUSED (proven in
    ``TestBoundedFetchFailures``). A page-fetcher dependency that is not
    structurally valid — no callable ``fetch``, or a ``fetch`` that returns
    a non-``FetchedPage`` — is a wiring/programming defect, NOT a network
    acquisition failure, and must propagate (``TypeError``) instead of
    being downgraded to a bounded authority status. There is no broad
    ``Exception`` catch anywhere in this module: a bare ``Exception`` and a
    ``RuntimeError`` (proven in ``TestProgrammingErrorsPropagate``) both
    propagate to the outer catastrophic boundary.
    """

    def test_non_callable_fetch_dependency_raises_type_error(self) -> None:
        class _NoFetchDependency:
            """A dependency that has no fetch method at all."""

        with pytest.raises(TypeError, match="callable fetch"):
            acquire_micron_alias_eligibility(
                request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
                page_fetcher=_NoFetchDependency(),
            )

    def test_non_callable_fetch_attribute_raises_type_error(self) -> None:
        fetcher = MagicMock(spec=PageFetcher)
        fetcher.fetch = "not a callable"  # type: ignore[method-assign]
        with pytest.raises(TypeError, match="not callable"):
            acquire_micron_alias_eligibility(
                request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
                page_fetcher=fetcher,
            )

    @pytest.mark.parametrize("wrong_return", [{"body": "a mapping is not a FetchedPage"}, "a string is not a FetchedPage", 42, None])
    def test_fetch_returning_non_fetched_page_raises_type_error(
        self, wrong_return: object
    ) -> None:
        fetcher = MagicMock(spec=PageFetcher)
        fetcher.fetch.return_value = wrong_return
        with pytest.raises(TypeError, match="must return a FetchedPage"):
            acquire_micron_alias_eligibility(
                request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
                page_fetcher=fetcher,
            )

    def test_exact_bare_exception_propagates(self) -> None:
        """A bare ``Exception("programming defect")`` is NOT a bounded
        authority failure: it propagates exactly as raised."""
        fetcher = MagicMock(spec=PageFetcher)
        fetcher.fetch.side_effect = Exception("programming defect")
        with pytest.raises(Exception) as caught:
            acquire_micron_alias_eligibility(
                request=ResearchRequest(manufacturer_part_number=BASER, description="d"),
                page_fetcher=fetcher,
            )
        assert type(caught.value) is Exception
        assert str(caught.value) == "programming defect"


class TestNoAuthorityPolicyInjectionSurface:
    """The reviewed v1 authority policy is fixed and caller-independent."""

    def test_signature_accepts_only_request_and_page_fetcher(self) -> None:
        import inspect

        signature = inspect.signature(acquire_micron_alias_eligibility)
        parameters = list(signature.parameters)
        assert parameters == ["request", "page_fetcher"]
        for parameter in signature.parameters.values():
            assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
            assert parameter.default is inspect.Parameter.empty

    def test_module_defines_no_public_policy_knobs(self) -> None:
        import product_intelligence.execution.micron_alias_authority as authority_module

        defined_here = {
            name: obj
            for name, obj in vars(authority_module).items()
            if getattr(obj, "__module__", None) == authority_module.__name__
        }
        public = {name for name in defined_here if not name.startswith("_")}
        assert public == {"acquire_micron_alias_eligibility"}
        # The policy itself must be module-private, never caller-reachable.
        assert "_MicronAliasAuthorityPolicy" in defined_here

    def test_no_url_origin_or_policy_knowledge_is_acceptable(self) -> None:
        # The reviewed catalog URL is fixed: no argument shape that lets a
        # caller substitute origin, URL, policy, or category evidence.
        for kwarg in (
            "catalog_url",
            "origin",
            "requested_url",
            "source_url",
            "policy",
            "policy_id",
            "manufacturer",
            "category",
            "alias_suffixes",
            "allowed_suffixes",
        ):
            with pytest.raises(TypeError):
                acquire_micron_alias_eligibility(
                    request=ResearchRequest(
                        manufacturer_part_number=BASER, description="d"
                    ),
                    page_fetcher=_fetcher_returning(_fixture_body()),
                    **{kwarg: "injected"},
                )
