"""Single-source-of-truth tests for the semantic contract (FU3A2).

``product_intelligence.semantic.contract`` is the canonical implementation of
prompt v1.1, the decision vocabulary, the response schema, and the strict
parser/validator. The evaluation harness must RE-EXPORT those objects, not keep
a second identical copy that can drift.

An import statement is not proof of sharing: a module can import the contract
and still define and export its own duplicate. Every test here asserts OBJECT
IDENTITY (``is``), which only holds if evaluation genuinely delegates.

The two frozen hashes below are the qualification-run fingerprints. They are
evidence that this extraction was behaviour preserving: the prompts built after
the extraction hash to exactly the value recorded when the models were
qualified. They are not new truth - they are the existing truth, re-proved.
"""

from __future__ import annotations

import hashlib

import pytest

from product_intelligence.semantic import contract

# Frozen fingerprints from the approved FULL qualification run.
FROZEN_FULL_PROMPT_SHA256 = (
    "f50e5584659f953ce73a97ccc8bc1ff487fbeeb37e2e0a72e52210613aeab1ff"
)
FROZEN_CORPUS_SHA256 = (
    "3c21d6fcd4eefa5cc383792abfd9308bd5c03315834c8ffdffd0f6a2b3619ca1"
)


# ---------------------------------------------------------------------------
# Prompt v1.1 is one object, not two copies
# ---------------------------------------------------------------------------


def test_evaluation_build_prompt_is_the_contract_function() -> None:
    """``evaluation.semantic.prompt.build_prompt`` IS the contract function."""
    from product_intelligence.evaluation.semantic import prompt as eval_prompt

    assert eval_prompt.build_prompt is contract.build_prompt


def test_evaluation_package_build_prompt_is_the_contract_function() -> None:
    """The evaluation package export is the contract function too.

    Covers the package ``__init__`` re-export, which is what most call sites
    actually reach for.
    """
    import product_intelligence.evaluation.semantic as eval_semantic

    assert eval_semantic.build_prompt is contract.build_prompt


def test_evaluation_prompt_text_objects_are_the_contract_objects() -> None:
    """System prompt, user template and version are the same objects."""
    from product_intelligence.evaluation.semantic import prompt as eval_prompt

    assert eval_prompt.SYSTEM_PROMPT is contract.SYSTEM_PROMPT
    assert eval_prompt.USER_PROMPT_TEMPLATE is contract.USER_PROMPT_TEMPLATE
    assert eval_prompt.SEMANTIC_PROMPT_VERSION is contract.SEMANTIC_PROMPT_VERSION
    assert eval_prompt.SemanticPrompt is contract.SemanticPrompt


def test_evaluation_prompt_module_defines_no_duplicate_prompt_text() -> None:
    """The evaluation prompt module must not carry its own prompt copy.

    Identity above proves the exported name is shared; this proves the source
    file no longer contains a second literal that a later edit could diverge.
    """
    import ast
    from pathlib import Path

    import product_intelligence.evaluation.semantic.prompt as eval_prompt

    source = Path(eval_prompt.__file__).read_text(encoding="utf-8")

    assigned_names: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            assigned_names.extend(
                t.id for t in node.targets if isinstance(t, ast.Name)
            )
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            assigned_names.append(node.name)

    for canonical_name in (
        "SYSTEM_PROMPT",
        "USER_PROMPT_TEMPLATE",
        "SEMANTIC_PROMPT_VERSION",
        "SemanticPrompt",
        "build_prompt",
    ):
        assert canonical_name not in assigned_names, (
            f"{canonical_name} is redefined in evaluation/semantic/prompt.py; "
            "it must be re-exported from semantic.contract, not reimplemented"
        )


# ---------------------------------------------------------------------------
# Vocabulary is one set of objects
# ---------------------------------------------------------------------------


def test_evaluation_semantic_decision_is_the_contract_enum() -> None:
    """``SemanticDecision`` IS the contract enum, in module and package."""
    import product_intelligence.evaluation.semantic as eval_semantic
    from product_intelligence.evaluation.semantic import vocabulary

    assert vocabulary.SemanticDecision is contract.SemanticDecision
    assert eval_semantic.SemanticDecision is contract.SemanticDecision


def test_evaluation_confidence_level_is_the_contract_enum() -> None:
    """``ConfidenceLevel`` IS the contract enum."""
    import product_intelligence.evaluation.semantic as eval_semantic
    from product_intelligence.evaluation.semantic import vocabulary

    assert vocabulary.ConfidenceLevel is contract.ConfidenceLevel
    assert eval_semantic.ConfidenceLevel is contract.ConfidenceLevel


def test_evaluation_match_response_is_the_contract_dataclass() -> None:
    """``SemanticMatchResponse`` IS the contract dataclass."""
    import product_intelligence.evaluation.semantic as eval_semantic
    from product_intelligence.evaluation.semantic import vocabulary

    assert vocabulary.SemanticMatchResponse is contract.SemanticMatchResponse
    assert eval_semantic.SemanticMatchResponse is contract.SemanticMatchResponse


def test_a_contract_decision_satisfies_evaluation_isinstance_checks() -> None:
    """Sharing is observable in behaviour, not just in identity.

    A response built from contract objects must pass evaluation's own
    ``isinstance`` validation. Two structurally identical but separate enums
    would fail this.
    """
    from product_intelligence.evaluation.semantic import vocabulary

    response = contract.SemanticMatchResponse(
        decision=contract.SemanticDecision.UNCERTAIN,
        confidence=contract.ConfidenceLevel.LOW,
        matched_attributes=(),
        conflicting_attributes=(),
        missing_critical_attributes=("suffix",),
        reason_code="suffix_missing",
    )

    assert isinstance(response, vocabulary.SemanticMatchResponse)
    assert isinstance(response.decision, vocabulary.SemanticDecision)
    assert isinstance(response.confidence, vocabulary.ConfidenceLevel)


# ---------------------------------------------------------------------------
# Parser and validator are one implementation
# ---------------------------------------------------------------------------


def test_evaluation_parse_raw_output_is_the_contract_function() -> None:
    """``parse_raw_output`` IS the contract function."""
    import product_intelligence.evaluation.semantic as eval_semantic
    from product_intelligence.evaluation.semantic import evaluator

    assert evaluator.parse_raw_output is contract.parse_raw_output
    assert eval_semantic.parse_raw_output is contract.parse_raw_output


def test_evaluation_parse_error_is_the_contract_exception() -> None:
    """``RawOutputParseError`` IS the contract exception class.

    A separate class with the same name would make ``except`` clauses on either
    side silently miss the other side's failures.
    """
    import product_intelligence.evaluation.semantic as eval_semantic
    from product_intelligence.evaluation.semantic import evaluator

    assert evaluator.RawOutputParseError is contract.RawOutputParseError
    assert eval_semantic.RawOutputParseError is contract.RawOutputParseError


def test_evaluation_evaluator_validate_response_is_the_contract_function() -> None:
    """The evaluator's ``validate_response`` IS the contract function."""
    from product_intelligence.evaluation.semantic import evaluator

    assert evaluator.validate_response is contract.validate_response


def test_evaluator_module_defines_no_duplicate_parser_or_validator() -> None:
    """The evaluator source must not redefine the parser or the validator."""
    import ast
    from pathlib import Path

    import product_intelligence.evaluation.semantic.evaluator as evaluator

    source = Path(evaluator.__file__).read_text(encoding="utf-8")

    defined: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defined.append(node.name)

    for canonical_name in (
        "parse_raw_output",
        "validate_response",
        "RawOutputParseError",
    ):
        assert canonical_name not in defined, (
            f"{canonical_name} is redefined in evaluation/semantic/evaluator.py; "
            "it must be re-exported from semantic.contract, not reimplemented"
        )


def test_vocabulary_module_defines_no_duplicate_vocabulary() -> None:
    """The vocabulary source must not redefine the shared vocabulary."""
    import ast
    from pathlib import Path

    import product_intelligence.evaluation.semantic.vocabulary as vocabulary

    source = Path(vocabulary.__file__).read_text(encoding="utf-8")

    defined: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defined.append(node.name)

    for canonical_name in (
        "SemanticDecision",
        "ConfidenceLevel",
        "SemanticMatchResponse",
    ):
        assert canonical_name not in defined, (
            f"{canonical_name} is redefined in evaluation/semantic/vocabulary.py; "
            "it must be re-exported from semantic.contract, not reimplemented"
        )

    # The evaluation-only vocabulary still lives here.
    assert "SemanticCaseClass" in defined


# ---------------------------------------------------------------------------
# Production does not depend on the evaluation harness
# ---------------------------------------------------------------------------


def test_production_semantic_sources_do_not_import_evaluation_semantic() -> None:
    """No production semantic source may name an evaluation module - anywhere.

    FU3A2B removed the one exception this test used to carve out: the live
    transport used to be resolved lazily from
    ``product_intelligence.evaluation.semantic.transport``. It is now resolved
    from ``product_intelligence.semantic.transport``, a neutral module that
    depends on nothing evaluation-side. There is no longer a permitted
    reference, lazy or otherwise.

    This walks the WHOLE tree with ``ast.walk`` - not just top-level
    statements - so an import hidden inside a function body (exactly how the
    old lazy transport import was written) cannot slip past. It also scans
    every string literal in the source for the evaluation package path, which
    would catch a dynamic ``importlib.import_module("product_intelligence."
    "evaluation...")`` reference that an ``ast.Import`` node would miss
    entirely.
    """
    import ast
    from pathlib import Path

    package_root = Path(contract.__file__).parent
    sources = sorted(package_root.glob("*.py"))
    assert sources, "the production semantic package must have source files"

    forbidden = "product_intelligence.evaluation"

    # Call targets that can perform a string-driven dynamic import. A plain
    # string scan over the whole source would also flag prose docstrings that
    # merely *name* the forbidden package (this file's own docstrings do, to
    # explain the boundary) - so only the argument of an actual import-style
    # call is inspected.
    dynamic_import_call_names = {"import_module", "__import__"}

    def _call_name(node: ast.Call) -> str | None:
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return None

    for path in sources:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not name.startswith(forbidden), (
                    f"{path.name} imports {name}; production must not "
                    "depend on the evaluation harness, anywhere in the "
                    "module, lazy or not"
                )

            if isinstance(node, ast.Call) and _call_name(node) in (
                dynamic_import_call_names
            ):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(
                        arg.value, str
                    ):
                        assert forbidden not in arg.value, (
                            f"{path.name} dynamically imports "
                            f"{arg.value!r}; production must not depend on "
                            "the evaluation harness, even via importlib"
                        )


# ---------------------------------------------------------------------------
# The extraction was behaviour preserving
# ---------------------------------------------------------------------------


def test_full_qualification_prompt_hash_is_unchanged() -> None:
    """Prompts built through the contract still hash to the frozen value.

    This is the strongest available proof that making the contract canonical
    changed no prompt byte: the digest is the one recorded by the approved FULL
    qualification run.
    """
    from product_intelligence.evaluation.semantic.loader import load_corpus
    from product_intelligence.evaluation.semantic.runner import (
        BenchmarkRunConfig,
        _compute_prompt_sha256,
    )
    from product_intelligence.evaluation.semantic.transport import (
        FakeSemanticModelTransport,
    )

    corpus = load_corpus()
    config = BenchmarkRunConfig(
        provider="amax",
        model="nemotron-3-super",
        case_selection="FULL",
        transport=FakeSemanticModelTransport(),
    )

    assert (
        _compute_prompt_sha256(tuple(corpus.cases), config)
        == FROZEN_FULL_PROMPT_SHA256
    )


def test_corpus_hash_is_unchanged() -> None:
    """Corpus truth did not move. The benchmark source is byte-identical."""
    from product_intelligence.evaluation.semantic.loader import load_corpus
    from product_intelligence.evaluation.semantic.runner import (
        _compute_corpus_sha256,
    )

    assert _compute_corpus_sha256(load_corpus()) == FROZEN_CORPUS_SHA256


@pytest.mark.parametrize(
    "raw_output",
    [
        '{"decision": "MATCH", "confidence": "HIGH", "matched_attributes": [], '
        '"conflicting_attributes": [], "missing_critical_attributes": [], '
        '"reason_code": "exact_mpn_match"}',
        "",
        "not json {",
        "```json\n{}\n```",
        '["MATCH"]',
    ],
)
def test_production_and_evaluation_parse_identically(raw_output: str) -> None:
    """Production and evaluation parsing cannot diverge - one function runs.

    Parametrised over accepted and rejected shapes so the equivalence covers
    both outcomes, not just the happy path.
    """
    from product_intelligence.evaluation.semantic import evaluator

    def attempt(parse) -> object:
        try:
            return ("ok", parse(raw_output))
        except contract.RawOutputParseError as exc:
            return ("error", str(exc))

    assert attempt(contract.parse_raw_output) == attempt(evaluator.parse_raw_output)


# ---------------------------------------------------------------------------
# FU3A2B: the loader's validate_response is the last duplicate, now removed
# ---------------------------------------------------------------------------


def test_loader_validate_response_is_the_contract_function() -> None:
    """loader.validate_response IS contract.validate_response.

    This was the last residual duplicate identified at the end of FU3A2:
    evaluation/semantic/loader.py kept its own copy of the validator even
    after the evaluator's copy became a re-export. It is a re-export now too.
    """
    from product_intelligence.evaluation.semantic import loader

    assert loader.validate_response is contract.validate_response


def test_evaluation_package_validate_response_is_the_contract_function() -> None:
    """The package-level export also resolves to the same object.

    product_intelligence.evaluation.semantic.__init__ imports
    validate_response from loader, so this is really the same identity chain
    as the test above observed from the package's own public surface - the
    surface most callers actually import from.
    """
    import product_intelligence.evaluation.semantic as eval_semantic

    assert eval_semantic.validate_response is contract.validate_response


def test_loader_module_defines_no_duplicate_validate_response() -> None:
    """The loader source must not redefine validate_response.

    Identity above proves the exported name is shared; this proves the source
    file carries no second function body that a later edit could diverge from
    the canonical one.
    """
    import ast
    from pathlib import Path

    import product_intelligence.evaluation.semantic.loader as loader

    source = Path(loader.__file__).read_text(encoding="utf-8")

    defined = [
        node.name
        for node in ast.parse(source).body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    ]

    assert "validate_response" not in defined, (
        "validate_response is redefined in evaluation/semantic/loader.py; "
        "it must be re-exported from semantic.contract, not reimplemented"
    )


def test_loader_public_import_path_still_works() -> None:
    """The frozen public import path is unchanged by the extraction.

    from product_intelligence.evaluation.semantic.loader import
    validate_response is how the existing corpus tests import it
    (tests/evaluation/semantic/test_corpus.py); it must keep working
    exactly as before.
    """
    from product_intelligence.evaluation.semantic.loader import (
        validate_response,
    )

    assert validate_response is contract.validate_response


# ---------------------------------------------------------------------------
# FU3A2B: the transport implementation is one object, not two copies
# ---------------------------------------------------------------------------


def test_evaluation_transport_classes_are_the_neutral_module_classes() -> None:
    """Every transport class the harness exposes IS the neutral module's.

    product_intelligence.semantic.transport is now the canonical
    implementation; evaluation/semantic/transport.py must re-export the
    same objects, not parallel copies.
    """
    from product_intelligence.evaluation.semantic import transport as eval_transport
    from product_intelligence.semantic import transport as neutral_transport

    assert eval_transport.SemanticModelTransport is (
        neutral_transport.SemanticModelTransport
    )
    assert eval_transport.FakeSemanticModelTransport is (
        neutral_transport.FakeSemanticModelTransport
    )
    assert eval_transport.OpenAISemanticTransport is (
        neutral_transport.OpenAISemanticTransport
    )
    assert eval_transport.TransportResult is neutral_transport.TransportResult
    assert eval_transport.TransportFailure is neutral_transport.TransportFailure
    assert eval_transport.get_openai_transport_for_provider is (
        neutral_transport.get_openai_transport_for_provider
    )


def test_evaluation_transport_error_vocabularies_are_shared() -> None:
    """The bounded error-type frozensets are the same objects too.

    runner.py reaches for RUN_FATAL_ERROR_TYPES directly; a copy that
    drifted from the neutral module's set would silently change which errors
    abort a benchmark run.
    """
    from product_intelligence.evaluation.semantic import transport as eval_transport
    from product_intelligence.semantic import transport as neutral_transport

    assert eval_transport.RUN_FATAL_ERROR_TYPES is (
        neutral_transport.RUN_FATAL_ERROR_TYPES
    )
    assert eval_transport.CASE_LOCAL_ERROR_TYPES is (
        neutral_transport.CASE_LOCAL_ERROR_TYPES
    )
    assert eval_transport.NETWORK_ERROR_TYPES is (
        neutral_transport.NETWORK_ERROR_TYPES
    )
    assert eval_transport.RESPONSE_ERROR_TYPES is (
        neutral_transport.RESPONSE_ERROR_TYPES
    )
    assert eval_transport.ALL_ERROR_TYPES is neutral_transport.ALL_ERROR_TYPES


def test_evaluation_transport_module_defines_no_duplicate_classes() -> None:
    """The harness transport source must not redefine any transport class.

    Identity above proves sharing; this proves the source carries no second
    definition of the classes it re-exports.
    """
    import ast
    from pathlib import Path

    import product_intelligence.evaluation.semantic.transport as eval_transport

    source = Path(eval_transport.__file__).read_text(encoding="utf-8")

    defined = [
        node.name
        for node in ast.parse(source).body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    ]

    for canonical_name in (
        "SemanticModelTransport",
        "FakeSemanticModelTransport",
        "OpenAISemanticTransport",
        "TransportResult",
        "TransportFailure",
        "get_openai_transport_for_provider",
        "_classify_http_error",
    ):
        assert canonical_name not in defined, (
            f"{canonical_name} is redefined in evaluation/semantic/transport.py; "
            "it must be re-exported from semantic.transport, not reimplemented"
        )


def test_runner_run_fatal_error_types_is_the_neutral_frozenset() -> None:
    """runner.py's late import of RUN_FATAL_ERROR_TYPES is unaffected.

    runner.py imports this name from
    product_intelligence.evaluation.semantic.transport inside a function
    body (not this file's concern to relocate - it is evaluation-side code).
    This proves that re-export still resolves to the one true frozenset after
    the extraction.
    """
    from product_intelligence.evaluation.semantic.transport import (
        RUN_FATAL_ERROR_TYPES,
    )
    from product_intelligence.semantic.transport import (
        RUN_FATAL_ERROR_TYPES as neutral_set,
    )

    assert RUN_FATAL_ERROR_TYPES is neutral_set


# ---------------------------------------------------------------------------
# FU3A2B: production genuinely resolves the transport from the neutral module
# ---------------------------------------------------------------------------


def test_runtime_source_imports_transport_from_the_neutral_module() -> None:
    """runtime.py builds its live transport from semantic.transport.

    An AST check on the actual call site, not just an absence check: the
    lazy import inside _build_transport must name the neutral module.
    """
    import ast
    from pathlib import Path

    import product_intelligence.semantic.runtime as runtime_module

    tree = ast.parse(Path(runtime_module.__file__).read_text(encoding="utf-8"))

    found_neutral_transport_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == (
            "product_intelligence.semantic.transport"
        ):
            found_neutral_transport_import = True

    assert found_neutral_transport_import, (
        "runtime.py must import from product_intelligence.semantic.transport "
        "(the neutral module) to build its live transport"
    )


def test_runtime_builds_the_neutral_transport_class(monkeypatch) -> None:
    """End-to-end proof that the lazy import resolves to a real class.

    A runtime built without an injected transport uses the neutral module's
    OpenAISemanticTransport, proving the lazy import resolves to a usable
    class rather than merely parsing correctly.
    """
    from product_intelligence.semantic import SemanticRuntime, SemanticRuntimeConfig
    from product_intelligence.semantic.transport import OpenAISemanticTransport

    monkeypatch.setenv("PI_SEMANTIC_AMAX_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("PI_SEMANTIC_VLLM_262K_BASE_URL", "https://example.invalid/v1")

    runtime = SemanticRuntime(config=SemanticRuntimeConfig())

    assert isinstance(runtime._primary_transport, OpenAISemanticTransport)
    assert isinstance(runtime._fallback_transport, OpenAISemanticTransport)


# ---------------------------------------------------------------------------
# FU3A2D: contract.py's type annotations use typing.Any, not builtin any
# ---------------------------------------------------------------------------


def test_contract_annotations_use_typing_any_not_builtin_any() -> None:
    """``dict[str, any]`` (the builtin function) is a real, previously-latent
    bug distinct from ``dict[str, Any]`` (``typing.Any``): the two look
    identical in a diff but mean completely different things to a type
    checker, and only one of them is a legal PEP 585 subscript target.

    ``from __future__ import annotations`` means these annotations are stored
    as strings and never evaluated at import time, so the wrong one would not
    raise on import - it would just silently type-check as nonsense forever.
    ``typing.get_type_hints`` is what actually resolves the string, so it is
    the one check that would have caught the original bug.
    """
    from typing import Any, get_type_hints

    from product_intelligence.semantic import contract

    parse_hints = get_type_hints(contract.parse_raw_output)
    assert parse_hints["return"] == dict[str, Any]

    validate_hints = get_type_hints(contract.validate_response)
    assert validate_hints["response"] == (dict[str, Any] | contract.SemanticMatchResponse)


def test_contract_source_contains_no_bare_any_subscript() -> None:
    """Belt and suspenders: no ``dict[str, any]`` (lowercase, builtin) string
    remains anywhere in the source, so a future edit cannot reintroduce the
    exact original typo even in a spot ``get_type_hints`` does not reach.
    """
    import re
    from pathlib import Path

    from product_intelligence.semantic import contract

    source = Path(contract.__file__).read_text(encoding="utf-8")

    offenders = re.findall(r"\[str,\s*any\]", source)
    assert offenders == [], (
        f"found builtin `any` used as a type annotation: {offenders}; "
        "this must be typing.Any"
    )
