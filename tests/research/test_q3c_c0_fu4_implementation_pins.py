"""Q3-C-C0: FU4 implementation integrity pinning (the CF-2 correction).

PRODUCT-INTEL.Q3-C-C0 (design §9.2 of
``docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_QUALIFICATION_DESIGN.md``)
resolves finding CF-2: at the C0 starting SHA the two frozen FU4
authority modules — the deterministic authority derivation
(``semantic_authority_fu4.py``) and the R1 record / codec / replay
adapter (``semantic_decision_v2_fu4.py``) — carried NO file-content pin
in any test literal (verified by exhaustive grep across ``tests/`` +
``docs/`` before the pin). These modules are the qualified surface the
future Q3-C Track A execution will evaluate; qualification results over
an unpinned implementation identity are only as strong as the pin, so
the contract is restored here BEFORE any Track A execution (R-C1-1),
following the recorded R1-FU1 / R2-FU1 precedent (a content pin is a
LITERAL recorded at the pinning phase, never computed from the file
under test at run time).

This module is the designated C0 pin home (the task's preferred
separate small test module; it is NOT added to the FU4 A1 suite). Each
pinned module is covered by exactly one node (two nodes total — the
design §9.2 acceptance: collection 7574 -> 7576, +2), and each node
verifies the module's implementation identity against LITERAL
recorded digests.

SUBPROCESS-FREE IMPLEMENTATION (this correction's recorded mandate).
The integrity nodes use ``pathlib`` (file bytes) and ``hashlib``
(SHA-256) ONLY: no git invocation, no object-store access, and no
``subprocess`` import anywhere in this module. Git commands were used
exclusively during the C0 setup / documentation pass to record the
fixed audit metadata below; normal pytest execution never touches git.
The earlier subprocess + loose-object variant of these nodes was
rejected for exactly this reason: under Windows handle pressure the
git subprocess itself flakes, which would turn a content-integrity
contract into a member of the load-sensitive flake class. The fixed
eleven-node allowlist is NOT expanded; these two nodes must never
join it.

FIXED AUDIT METADATA (recorded once, at the C0 setup; NOT re-derived
at run time). Derivation procedure of record (executed at setup only,
over the starting SHA):

* blob OID (the committed Git blob object ID):
    ``git rev-parse a3134739fdf2531f295744e832099f17f06acfbd:
      product_intelligence/research/<module>.py``
* committed content size / bytes / SHA-256:
    ``git cat-file -s <blob_oid>``
    ``git cat-file blob <blob_oid> | sha256sum``
  (the stored blob bytes — NO clean / smudge filter applied)

``semantic_authority_fu4.py``:
    blob OID        7c1b1c4f8e88b8951e9362087aeb6b40f7aaf8bd
    committed size  167,523 bytes (pure LF, 3,614 lines)
    committed SHA-256
                    482a637477dd24dfbb1051f714ab087b96061f80
                    c8617ce8adb421a4edb5c09f
``semantic_decision_v2_fu4.py``:
    blob OID        8a4c62c8d360a489740e244f312be1e35ed52fa8
    committed size  123,142 bytes (pure LF, 3,030 lines)
    committed SHA-256
                    c1037a5a987ee7a1674de0d9736ec9670ef13737
                    e092a857b643ea70548d1224

CRLF / LF PORTABILITY (the explicitly documented, bounded
normalization policy). The repository is checked out with
``core.autocrlf=true`` + ``.gitattributes`` ``* text=auto``, so a
committed pure-LF blob may legitimately appear in the working tree as
its exact CRLF expansion (every ``\\n`` -> ``\\r\\n``; the expansion
adds one byte per line and touches nothing else). The policy is
bounded to exactly that one transformation and no other:

* ``content := raw.replace(b"\\r\\n", b"\\n")`` — the SOLE
  normalization, applied ONLY to derive assertion A. It is the exact
  inverse of the autocrlf checkout expansion. No whitespace trimming,
  no encoding conversion, no lone-CR handling, no trailing-newline
  logic, no arbitrary content rewriting: any byte difference other
  than line-ending state survives the normalization and changes the
  digest.
* EVERY expected digest in this module is a LITERAL recorded at the
  C0 setup (the committed-content SHA-256 + size, and the two
  documented checkout-state raw digests below). No expected value is
  ever computed from the file under test at run time.

EACH NODE ASSERTS TWO SEPARATE IDENTITIES (neither conflated, neither
weakened).

A. CONTENT IDENTITY (portable across the two documented checkout
   states): the working-tree bytes, after the bounded CRLF->LF
   normalization, must be byte-identical to the committed approved
   content — asserted by size AND SHA-256 against the literals above.
   This is the pin of the exact approved content: a content change in
   either module fails its own node here, in any documented checkout
   state.

B. WORKING-TREE STATE (the house pin convention, design §2.7): the
   RAW working-tree bytes (NO normalization) must hash to exactly one
   of the two recorded checkout-state literals — the pure-LF committed
   form, or the exact CRLF expansion of it. The C0 recording machine
   sits in a DIFFERENT documented state for the two modules, and both
   states are pinned exactly as recorded:

   * ``semantic_authority_fu4.py`` — checked out CRLF-expanded here
     (171,137 bytes = 167,523 + 3,614 line endings; raw digest
     ``0a0fb3d7...`` = the CRLF literal; ``git diff``-clean because
     git normalizes the expansion, §2.7).
   * ``semantic_decision_v2_fu4.py`` — checked out byte-IDENTICAL to
     the committed blob here (pure LF; raw digest ``c1037a5a...`` =
     the committed literal).

   A mixed line-ending state, a lone-CR residue, or any other byte
   change is NOT a documented checkout state: it fails assertion B
   loudly — a recorded re-pin event (design R-C1-2), never a silent
   one. A checkout-state change (e.g. a fresh clone under a
   different autocrlf configuration) moves the raw digest to the
   OTHER recorded literal and keeps passing — the documented,
   intended portability.

RE-PINNING DISCIPLINE. The literals are frozen at the C0 starting SHA
(``a3134739fdf2531f295744e832099f17f06acfbd``, the D1 design endpoint;
the two production files are byte-identical between the R2-FU1
endpoint ``3bf6eb294df3ca83b93665158297f97abf3fba4b`` and this SHA).
Any legitimate modification of either module requires an explicit,
separately reviewed phase that re-records the literals with its own
starting SHA (the R1-FU1 / R2-FU1 recorded-re-pin pattern). Editing
the file to make this test pass — or editing these literals to match
a changed file — is a contract violation, not a fix. C0 grants NO
qualification: pinning the implementation identity does not make the
FU4 authority qualified, production-approved, or pricing-eligible.
"""

from __future__ import annotations

import hashlib
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The C0 starting SHA (HEAD at the C0 preflight; the Q3-C-D1 design
#: endpoint). The fixed audit metadata in this module was recorded AT
#: THIS SHA during the setup pass (git at setup only — see the module
#: docstring). It is NOT re-derived during pytest execution.
C0_STARTING_SHA = "a3134739fdf2531f295744e832099f17f06acfbd"


def _module_record(
    path: str,
    blob_oid: str,
    committed_sha256: str,
    committed_size: int,
    crlf_variant_sha256: str,
    crlf_variant_size: int,
    recorded_checkout_state: str,
) -> dict:
    return {
        "path": path,
        "blob_oid": blob_oid,
        "committed_sha256": committed_sha256,
        "committed_size": committed_size,
        "crlf_variant_sha256": crlf_variant_sha256,
        "crlf_variant_size": crlf_variant_size,
        "recorded_checkout_state": recorded_checkout_state,
    }


#: The two pinned modules (the CF-2 gap of record). Every value is a
#: LITERAL recorded at the C0 setup (the docstring's audit block) —
#: never derived from the files under test at run time.
FU4_AUTHORITY_MODULE = _module_record(
    path="product_intelligence/research/semantic_authority_fu4.py",
    # Fixed audit metadata (setup-time git derivation of record).
    blob_oid="7c1b1c4f8e88b8951e9362087aeb6b40f7aaf8bd",
    # Committed content (pure LF, 3,614 lines): SHA-256 + size.
    committed_sha256=(
        "482a637477dd24dfbb1051f714ab087b96061f80c8617ce8adb421a4edb5c09f"
    ),
    committed_size=167_523,
    # The exact CRLF expansion of the committed content (167,523 +
    # 3,614 line-ending bytes = 171,137) — the checkout state of the
    # recording machine.
    crlf_variant_sha256=(
        "0a0fb3d7760208b03ca54b7e12e35e8fa9bed81e0e09898252b4cecb2cf81bc4"
    ),
    crlf_variant_size=171_137,
    recorded_checkout_state="CRLF-expanded here (autocrlf machine state)",
)

R1_RECORD_ADAPTER_MODULE = _module_record(
    path="product_intelligence/research/semantic_decision_v2_fu4.py",
    # Fixed audit metadata (setup-time git derivation of record).
    blob_oid="8a4c62c8d360a489740e244f312be1e35ed52fa8",
    # Committed content (pure LF, 3,030 lines): SHA-256 + size.
    committed_sha256=(
        "c1037a5a987ee7a1674de0d9736ec9670ef13737e092a857b643ea70548d1224"
    ),
    committed_size=123_142,
    # The exact CRLF expansion of the committed content (123,142 +
    # 3,030 line-ending bytes = 126,172) — the OTHER documented
    # checkout state (the recording machine holds this file in the
    # LF state).
    crlf_variant_sha256=(
        "f6f0eecf98a544bd70adb1b47203f149b2ee8710a6d19b8e6947d5f681755967"
    ),
    crlf_variant_size=126_172,
    recorded_checkout_state="byte-identical to the committed LF blob here",
)

PINNED_MODULES = (FU4_AUTHORITY_MODULE, R1_RECORD_ADAPTER_MODULE)


def _normalize_line_endings(raw: bytes) -> bytes:
    """The C0 bounded normalization policy (module docstring): the
    SOLE transformation applied to working-tree bytes before
    assertion A — every CRLF (0x0D 0x0A) becomes LF (0x0A), the exact
    inverse of the ``core.autocrlf`` checkout expansion. NO other byte
    is touched: a lone CR, a mixed line-ending state, or any content
    difference survives and changes the digest.
    """
    return raw.replace(b"\r\n", b"\n")


class TestQ3CC0FU4ImplementationIntegrityPins:
    """The CF-2 pin-gap correction: the two frozen FU4 authority
    modules are content-pinned at the C0 starting SHA — one node per
    module (design §9.2 acceptance: +2 nodes, 7574 -> 7576). Each node
    is subprocess-free (``pathlib`` + ``hashlib`` only) and verifies,
    against LITERAL recorded digests, the exact approved content
    (assertion A) and the working-tree checkout state (assertion B).
    Any unexpected change to a module fails its own node (and only its
    own); a legitimate modification requires an explicit, separately
    reviewed phase and a recorded re-pin — never an in-place digest
    edit, and never a silent line-ending re-pin (R-C1-2).
    """

    @pytest.mark.parametrize(
        "module",
        PINNED_MODULES,
        ids=["semantic_authority_fu4", "semantic_decision_v2_fu4"],
    )
    def test_pinned_module_implementation_identity_is_unchanged(
        self, module: dict
    ) -> None:
        path = module["path"]
        try:
            raw = (REPO_ROOT / path).read_bytes()
        except OSError as exc:
            raise AssertionError(
                f"{path}: the working-tree file is unreadable ({exc!r}) "
                f"— the C0 implementation identity cannot be verified. A "
                f"missing pinned module is a contract failure requiring "
                f"explicit review, not a silent pass"
            ) from exc

        # -----------------------------------------------------------
        # A. CONTENT IDENTITY — the exact approved content (portable
        #    across the two documented checkout states).
        # -----------------------------------------------------------
        content = _normalize_line_endings(raw)
        assert len(content) == module["committed_size"], (
            f"{path}: content size (after the bounded CRLF->LF "
            f"normalization) is {len(content)} bytes, not the recorded "
            f"C0 pin {module['committed_size']} (blob "
            f"{module['blob_oid']} at starting SHA {C0_STARTING_SHA}). "
            f"A size change means the content changed — any legitimate "
            f"modification requires an explicit, separately reviewed "
            f"phase and a recorded re-pin, never an in-place digest "
            f"edit"
        )
        assert (
            hashlib.sha256(content).hexdigest() == module["committed_sha256"]
        ), (
            f"{path}: content SHA-256 (after the bounded CRLF->LF "
            f"normalization) is "
            f"{hashlib.sha256(content).hexdigest()}, not the recorded "
            f"C0 pin {module['committed_sha256']} (blob "
            f"{module['blob_oid']}, {module['committed_size']} bytes, "
            f"at starting SHA {C0_STARTING_SHA}). The FU4 "
            f"qualified-surface content changed; any legitimate "
            f"modification requires an explicit, separately reviewed "
            f"phase and a recorded re-pin"
        )

        # -----------------------------------------------------------
        # B. WORKING-TREE STATE (house pin convention, design §2.7) —
        #    the RAW bytes (NO normalization) must be exactly one of
        #    the two recorded checkout states: the pure-LF committed
        #    form, or the exact CRLF expansion of it.
        # -----------------------------------------------------------
        raw_sha = hashlib.sha256(raw).hexdigest()
        allowed_raw_digests = (
            module["committed_sha256"],
            module["crlf_variant_sha256"],
        )
        assert raw_sha in allowed_raw_digests, (
            f"{path}: working-tree SHA-256 is {raw_sha} ({len(raw)} "
            f"bytes), which is neither the recorded pure-LF committed "
            f"form {module['committed_sha256']} nor the recorded exact "
            f"CRLF expansion {module['crlf_variant_sha256']} "
            f"({module['crlf_variant_size']} bytes; "
            f"{module['recorded_checkout_state']}). Only those two "
            f"checkout states are documented (design §2.7 / R-C1-2): a "
            f"mixed line-ending state or any byte change fails here "
            f"loudly — a recorded re-pin event, never a silent one"
        )
