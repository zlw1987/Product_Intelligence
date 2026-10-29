# PERF-SEM-INV1-FU2 — Final Technical Correction Report

**Investigation type:** Corrective investigation (read-only). No implementation.
**Production baseline SHA:** `cde2a802c54372da088a7d1876f450cbf9bd7c69` (2026-10-26 15:53:55 -0700)
**Divergent main branch SHA (NOT production):** `916296af8d23f780aca63702e3302458ba7f8ffd`
**Supersedes:** `docs/VENDOR_LOOKUP_FAILURE_INV1_CORRECTION.md` (PERF-SEM-INV1-FU1), which remains in place as the pre-correction record.
**Verification environment:** Python 3.14.7 (repository `.venv`) and Python 3.11.9 (32-bit), offline, no network access. All production-code inspection via `git show cde2a80:<path>`.

---

## 0. Status of the two FU2 findings

| Finding | Disposition |
|---|---|
| T1 — FU1 §4.3 "KEY FINDING" (urllib proxy analysis) | **RETRACTED and corrected** (Section 2). The V1 semantic transport's opener **does permit** ambient/system proxy configuration. |
| T2 — FU1 §6.3/§6.4 recommendation (persist full `SemanticRuntimeResult.to_dict()` into `ExecutionEvidenceRecord.semantic_provenance`) | **WITHDRAWN** (Section 3). Two bounded alternatives (A/B) are compared; neither is implemented; neither is recommended at this time. |
| T3 — Practical next action | **Diagnose the running WinSW service's effective environment and connectivity first** (Section 4), via CMD-only read-only diagnostics. |

Additional small correction found while re-verifying FU1's accepted content:
FU1 §2.2 states `PRIMARY_FALLBACK_ELIGIBLE_ERRORS` has "15 codes"; the production
frozenset has **14** members (FU1's own list contains 14 items). The frozen test
`tests/semantic/test_runtime.py::TestFallbackAllowlist::
test_allowlist_contents_are_exactly_the_qualified_set` (line 500 at the production
SHA) pins exactly those 14. `SemanticAttemptStatus` has 20 members: `OK` + the
14 fallback-eligible + 5 fail-closed (`INVALID_REQUEST_CONFIGURATION`,
`UNSUPPORTED_PARAMETER`, `PROVIDER_NOT_CONFIGURED`, `CASE_REJECTED`,
`UNKNOWN_ERROR`).

---

## 1. Accepted findings from FU1 (carried forward, re-verified at production SHA)

Each item below was re-verified against `cde2a80:<path>` during this correction.

1. **Production baseline is V1-only.** `git show cde2a80:...` returns exit 128 for
   `product_intelligence/semantic/runtime_v2.py`,
   `product_intelligence/execution/semantic_decision_v2_execution.py`,
   `product_intelligence/execution/semantic_decision_persistence.py`,
   `product_intelligence/semantic/contract_v2.py`,
   `product_intelligence/semantic/contract_v2_1.py`. (FU1 §1.3 — accepted.)

2. **V1 pinned route constants** (`product_intelligence/semantic/runtime.py` at
   production SHA): `PRIMARY_PROVIDER = "amax"`, `PRIMARY_MODEL = "qwen3.8-27b"`,
   `FALLBACK_PROVIDER = "vllm-262k"`, `FALLBACK_MODEL = "Qwen3.6-27B-262K"`,
   `SEMANTIC_TEMPERATURE = 0.0`, `SEMANTIC_MAX_TOKENS = 32768`,
   `DEFAULT_REQUEST_TIMEOUT_SECONDS = 300.0` (line 90). (FU1 §1.5 — accepted.)

3. **One `SemanticRuntimeResult` per eligible candidate, 1–2 attempts.**
   `SemanticRuntime.evaluate()` (line 1046): primary attempt → on `OK` returns a
   1-attempt success; on a fallback-eligible status exactly one fallback attempt;
   on a non-fallback-eligible status a 1-attempt failure. (FU1 §2.2 — accepted,
   with the 14-member correction in Section 0.)

4. **Fallback-eligible set is a frozen allowlist of 14 codes**
   (`runtime.py` lines 142–164): TIMEOUT, DNS_ERROR, TLS_ERROR, CONNECTION_ERROR,
   RATE_LIMITED, HTTP_ERROR, PROVIDER_UNAVAILABLE, AUTHENTICATION_FAILED,
   MODEL_NOT_FOUND, EMPTY_RESPONSE, MALFORMED_JSON, SCHEMA_INVALID,
   MODEL_IDENTITY_MISMATCH, INVALID_RESPONSE. (FU1 §2.2 — accepted, count
   corrected.)

5. **Per-attempt latency is measured in memory and never persisted.**
   `SemanticAttempt` (line 387) carries `latency_ms` validated in
   `__post_init__` (finite, ≥ 0); `_attempt()` (line 1172) measures it with
   `time.perf_counter()`. `ExecutionEvidenceRecord`
   (`product_intelligence/runs/models.py` line 488) has no latency field; its
   complete field set is: `run`, `attempt_number`, `stage` (Char 16, choices),
   `outcome` (Char 16, choices), `candidate_url` (TextField), `detail_code`
   (Char 64), `created_at`. (FU1 §3.5/§4.5/§4.6 — accepted.)

6. **`CONNECTION_ERROR` classification** in
   `OpenAISemanticTransport.complete()` (transport.py lines 570–596):
   `URLError` with `TimeoutError` reason → TIMEOUT; `URLError` with `OSError`
   reason or other reason → CONNECTION_ERROR; bare `TimeoutError` → TIMEOUT;
   bare `OSError`/`UnicodeDecodeError` → CONNECTION_ERROR.
   (FU1 §4.1 — accepted.)

7. **10 persisted SEMANTIC records; up to 20 model calls** (10–20 range) for the
   Micron production run; the 21 stderr `CONNECTION_ERROR` warnings are not
   definitively attributed to that single run. (FU1 §3.3–3.4, §7.3 — accepted.)

8. **The strict evidence contract is frozen and tested.**
   `product_intelligence/execution/evidence_writer.py`:
   `_VALID_COMBINATIONS` (line 139) — for SEMANTIC: SUCCESS →
   {`SEMANTIC_MATCH`, `SEMANTIC_NO_MATCH`, `SEMANTIC_UNCERTAIN`} (lines 200–204),
   FAILED → {`SEMANTIC_UNAVAILABLE`} (lines 205–206);
   `ExecutionEvidenceWriter.append_execution_attempt()` (line 316); strict reader
   `read_execution_evidence()` (line 411) validating contiguity, vocabularies,
   URL safety, and combinations. Pinned by
   `tests/execution/test_4c_b_corrective_pass.py`
   (`TestStrictEvidenceReaderImpossibleCombinations`,
   `TestLegalCombinationTable`, `TestStrictEvidenceWriterMalformedUrl`) and
   `tests/execution/test_execution_orchestration.py`.
   (FU1 §6.2 — accepted.)

9. **Safe candidate↔log correlation** via the 8-char SHA-256 prefix of
   `candidate_url` (`semantic_integration.py::_candidate_case_id`, line 296:
   `f"candidate-{url_hash}-{index}"`). (FU1 §3.7 — accepted.)

10. **Vendor adapter deliberately disables ambient proxy** (unlike the semantic
    transport — see Section 2.6):
    `product_intelligence/providers/internal_vendor.py::_build_vendor_opener`
    (line 183) uses `build_opener(ProxyHandler({}), <NoRedirect subclass>)`
    (line 196), with module docstring "no ambient proxy; explicit empty
    ProxyHandler({}) disables environment proxy routing" (line 22).
    (FU1 §4.3 — the vendor half of this claim is accepted.)

11. **All FU1 §7 retractions stand** (no V2 at production; no fixed 30 s
    inference; not-every-Primary-failed; errors not instant; no V2
    `SemanticDecisionAttempt` proposal).

---

## 2. Task 1 — Corrected urllib proxy analysis

### 2.1 Retracted claim (exact FU1 text)

FU1 §4.3, "KEY FINDING":

> "The V1 semantic transport does NOT install a proxy handler. It uses the bare
> `urllib.request.build_opener(NoRedirectHandler)`. Ambient
> `HTTP_PROXY`/`HTTPS_PROXY` environment variables are NOT used by this
> transport. This means proxy configuration issues would NOT affect the
> semantic transport unless the underlying network stack itself is configured
> to route through a proxy (system-level, not Python-level)."

**This is incorrect and is retracted.** `build_opener(NoRedirectHandler)`
**does** attempt to install the default `ProxyHandler`, and when ambient
proxy configuration exists in the process environment, the V1 semantic
transport **routes through that proxy**. The FU1 author apparently observed a
no-proxy host and generalized the observation into a claim about the code.
Also retracted: the FU1 §4.3 evidence-table row "Proxy issue | … NO proxy
handler is installed, so ambient proxy env vars are ignored for the semantic
transport … Neither semantic transport uses a proxy."

### 2.2 What the production V1 code actually does

`product_intelligence/semantic/transport.py` at `cde2a80`, in
`OpenAISemanticTransport._make_request()` (line 610):

```python
        # Use a redirect handler that does NOT follow redirects
        # This ensures 3xx responses fail closed rather than forwarding
        # the Authorization header to an unintended destination
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None  # Don't follow redirect

        opener = urllib.request.build_opener(NoRedirectHandler)

        try:
            with opener.open(req, timeout=self._request_timeout_seconds) as response:
```

(line 636–643). Facts of record:

- `NoRedirectHandler` is a subclass of **`HTTPRedirectHandler`** — it suppresses
  only the default redirect handler. It is **not** a `ProxyHandler` and
  suppresses nothing proxy-related.
- A **fresh opener is built on every `_make_request()` call**, i.e. per
  request. Therefore proxy discovery (see 2.3) is re-evaluated **per request**;
  environment or registry changes take effect on the next request without any
  process restart.

### 2.3 Verified stdlib behavior (offline; no network)

Source verified from `Lib/urllib/request.py`, byte-identical between
**Python 3.11.9 and Python 3.14.7** for: `build_opener`,
`OpenerDirector.add_handler`, `ProxyHandler.__init__`, `getproxies`,
`ProxyHandler.proxy_open`, `proxy_bypass_environment` (bracketing the
Python 3.12 production baseline declared in `pyproject.toml`).

**(a) `build_opener` installs a default `ProxyHandler` unless an explicit
`ProxyHandler` replacement is supplied.**

```python
    opener = OpenerDirector()
    default_classes = [ProxyHandler, UnknownHandler, HTTPHandler,
                       HTTPDefaultErrorHandler, HTTPRedirectHandler,
                       FTPHandler, FileHandler, HTTPErrorProcessor,
                       DataHandler]
    ...
    skip = set()
    for klass in default_classes:
        for check in handlers:
            if isinstance(check, type):
                if issubclass(check, klass):
                    skip.add(klass)
            elif isinstance(check, klass):
                skip.add(klass)
    ...
    for klass in default_classes:
        opener.add_handler(klass())
```

Passing `NoRedirectHandler` (a subclass of `HTTPRedirectHandler`) puts only
`HTTPRedirectHandler` into `skip`. `ProxyHandler` remains in
`default_classes`, so `opener.add_handler(ProxyHandler())` **is called**.

**(b) What `ProxyHandler()` (no argument) captures.**

```python
    def __init__(self, proxies=None):
        if proxies is None:
            proxies = getproxies()
        ...
        for type, url in proxies.items():
            type = type.lower()
            setattr(self, '%s_open' % type, ...)
```

and

```python
    def getproxies():
        return getproxies_environment() or getproxies_registry()
```

- `getproxies_environment()` reads **any environment variable ending in
  `_proxy`/`_PROXY`** (case-insensitive) — i.e. `HTTP_PROXY`, `http_proxy`,
  `HTTPS_PROXY`, `https_proxy`, `NO_PROXY`, `no_proxy` (→ key `no`), etc.
  (A CGI guard — `REQUEST_METHOD` in the environment — drops
  non-lowercase `HTTP_PROXY`; the WinSW/Waitress service is **not** a CGI
  context, so both cases are honored.)
- `getproxies_registry()` (Windows) reads
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings`:
  `ProxyEnable` + `ProxyServer` (WinINET system proxy). **Only when
  `getproxies_environment()` returns an empty mapping.** It does **not** use
  PAC/AutoConfig URLs.
- Which `HKCU` applies to the service process is the **service account's**
  user hive (e.g. `S-1-5-18`/`.DEFAULT` for LocalSystem), not the
  interactive operator's hive.

**(c) Registration is conditional on discovered proxies.**

`OpenerDirector.add_handler` only registers a handler that exposes at least
one protocol method (`added = True` gate; `proxy_open`/`do_open`/
`redirect_request` are explicitly skipped as "coincidental match"). Because
`ProxyHandler.__init__` binds `<type>_open` methods **only for protocols found
in the proxies mapping**:

- `getproxies()` non-empty (e.g. `HTTPS_PROXY` set, or WinINET proxy enabled)
  → `ProxyHandler` instance gains `https_open`/`http_open` → **registered**
  → requests are routed via the proxy (`ProxyHandler.proxy_open` calls
  `req.set_proxy(hostport, proxy_type)` after a per-request
  `proxy_bypass(req.host)` check).
- `getproxies()` empty → instance has no `*_open` methods → **not registered**
  → the opener is proxy-less.

**(d) NO_PROXY bypass is evaluated per request** (`ProxyHandler.proxy_open`):

```python
        if req.host and proxy_bypass(req.host):
            return None
```

`proxy_bypass()` consults `getproxies_environment()` (the `no_proxy`
variable; comma-separated DNS suffixes, `*` wildcard, port stripped) or,
when no `*_proxy` env vars exist at all, the registry `ProxyOverride`.

### 2.4 Offline verification evidence (this workstation, no network)

Bounded experiment using only loopback (`127.0.0.1:9`, discard port, nothing
listening) and reserved unresolvable names (`*.invalid`); the V1-shape opener
(`build_opener(NoRedirectHandler)`) reconstructed verbatim from transport.py:

| Arm | Ambient config | `ProxyHandler` in `opener.handlers` | Request outcome | Interpretation |
|---|---|---|---|---|
| 1 (control) | none | **absent** | `gaierror [Errno 11001] getaddrinfo failed` | went **direct** (DNS for the target) |
| 2 | `HTTP_PROXY=HTTPS_PROXY=http://127.0.0.1:9` | **present**, keys `['http','https']` | `ConnectionRefusedError [WinError 10061]` to 127.0.0.1:9 | **routed to the proxy** (target DNS never consulted) |
| 3 | arm 2 + `NO_PROXY=fu2-loopback-check.invalid` | present, keys `['http','https','no']` | `gaierror [Errno 11001]` again | per-request bypass → **direct** |

Control: the vendor-adapter shape `build_opener(ProxyHandler({}), NoRedirectHandler)`
produces an opener with **no** `ProxyHandler` at all (explicit empty mapping
suppresses the default; nothing to bind).

On this workstation `getproxies()` is currently empty (no `*_proxy` env vars;
`ProxyEnable` absent/0 in the interactive user's WinINET key), which is why
arm 1 shows no proxy handler — the same no-proxy state the FU1 author
apparently observed. **That state is a property of the observed host, not of
the code.**

### 2.5 Answers to the four required questions

**(1) Does the current opener permit environment/system proxy configuration?**
**Yes.** `build_opener(NoRedirectHandler)` (transport.py line 640) includes the
default `ProxyHandler`, which reads `getproxies()` — ambient `*_proxy`
environment variables **and**, on Windows, the WinINET registry proxy of the
process account — at opener-construction time (i.e. per semantic request, per
2.2). If any proxy is discovered, the request is routed through it. If none
is discovered, the handler is inert and the transport is proxy-less.

**(2) Is a proxy actually configured in the running WinSW service
environment?**
**UNKNOWN until evidenced.** The production deployment
(`C:\Product_Intelligence`, service `ProductIntelligencePilot`) is not present
on this workstation, so its effective environment cannot be read from here.
The service process's effective proxy inputs are exactly four, all readable
without touching the service (Section 4, steps D4–D7):
(i) WinSW XML `<environment>` entries, (ii) machine environment,
(iii) the service account's user environment, (iv) the service account's
WinINET `ProxyEnable`/`ProxyServer`. Section 4 supplies the CMD-only reads
and a decision table.

**(3) How may `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, and Windows proxy
discovery affect connectivity?**

- `HTTPS_PROXY` (or `https_proxy`) set in the service environment → **all**
  semantic calls (both providers, since both base URLs are read from
  `PI_SEMANTIC_AMAX_BASE_URL` / `PI_SEMANTIC_VLLM_262K_BASE_URL` and are
  HTTPS) are sent to that proxy (absolute-URI form / CONNECT tunnel). A proxy
  that is down, unreachable from the service account, or not permitted by
  egress firewalling produces `URLError` with `OSError` reason
  (`ConnectionRefusedError`, `timed out`, `Network unreachable`) → classified
  by the frozen transport as **CONNECTION_ERROR or TIMEOUT** — the exact
  bounded errors observed in the production run's stderr.
- `HTTP_PROXY` affects only non-HTTPS URLs; the semantic endpoints are HTTPS,
  so `HTTPS_PROXY` is the relevant variable.
- `NO_PROXY`/`no_proxy` (per-request, 2.3(d)) can exclude specific
  hosts/suffixes; `*` excludes all.
- Windows discovery: with **no** `*_proxy` env vars, the WinINET registry
  proxy of the **service account** applies. This can be non-empty even when
  no environment variable is visible in any CMD session — the single most
  likely source of an "invisible" proxy for the service.
- PAC (`AutoConfigURL`) is **not** consumed by urllib (registry read is
  `ProxyServer`/`ProxyEnable` only).
- The per-request opener rebuild (2.2) means a proxy configured or removed
  after service start changes behavior on the **next** request, without
  restart.
- The Waitress worker is the service process itself (single WinSW →
  python/waitress tree), so there is no separate worker environment to
  consider.

**(4) Why is disabling redirects not equivalent to disabling proxies?**
They are **independent default handler classes** in `build_opener`'s
`default_classes` list. `NoRedirectHandler` suppresses only the default
`HTTPRedirectHandler` (the `skip` logic matches on handler class). The
`ProxyHandler` default survives and is fully active whenever
`getproxies()` is non-empty (verified: arm 2 of 2.4 has both the redirect
handler disabled **and** a live proxy handler). Consequences: (i) a proxied
request whose proxy answers 3xx still fails closed (redirect not followed,
Authorization not forwarded — the intended FU3B2B security property is
preserved); (ii) conversely, the absence of redirects provides **no**
protection against ambient proxying — the request still leaves the machine
via the proxy's address first.

### 2.6 Cross-transport comparison at the production SHA (exact references)

| Transport | Opener construction | Ambient proxy? | Reference |
|---|---|---|---|
| Semantic V1 (`OpenAISemanticTransport`) | `build_opener(NoRedirectHandler)` — fresh per request | **Yes, if `getproxies()` non-empty** (default `ProxyHandler` installed) | `semantic/transport.py` lines 636–643 |
| Vendor lookup (`InternalVendorAdapter`) | `build_opener(ProxyHandler({}), <NoRedirect>)` — module-global, built once | **No** (explicit empty mapping suppresses the default and binds nothing) | `providers/internal_vendor.py` lines 183–201, docstring line 22 |
| 3A page fetcher | Hand-built `OpenerDirector` with `HTTPHandler`, `HTTPSHandler`, `_NoRedirectHandler`, `HTTPErrorProcessor`, `HTTPDefaultErrorHandler` only — no `ProxyHandler` class involved | **No** | `providers/http_page.py` lines 175–189 |
| Serper search | Bare `urllib.request.urlopen(request, ...)` → process-global opener from `build_opener()` (built once at first use) | **Yes, if `getproxies()` non-empty** at first use | `providers/serper.py` line 250 |

This asymmetry is directly diagnostic (Section 4): the vendor lookup and the
semantic transport have **different** exposure to the same ambient proxy, so
a proxy-caused fault pattern (semantic CONNECTION_ERRORs + vendor timeout,
page fetches fine) is observable.

### 2.7 Effect on the CONNECTION_ERROR attribution analysis

- FU1 §4.3's proxy row is **replaced**: proxy configuration **is** a live
  root-cause hypothesis for the semantic `CONNECTION_ERROR`/`TIMEOUT`
  failures, because the semantic transport inherits ambient proxy routing.
- The hypothesis remains **UNPROVEN** until the service-environment reads in
  Section 4 are executed. If steps D4–D7 find no proxy input for the service
  account, ambient proxy is **excluded** for the semantic transport and the
  differential diagnosis narrows to DNS/egress/firewall/upstream.
- FU1's remaining error-classification content (FU1 §4.1–§4.6, excluding the
  retracted proxy row and the count corrected in Section 0) is unchanged and
  stands.

### 2.8 Compliance

No proxy settings, transport code, or configuration were altered. No proxy
URLs, credentials, API keys, or private endpoints are printed in this report
or in the verification artifacts (the experiment used synthetic
`127.0.0.1:9` and `*.invalid` names only).

---

## 3. Task 2 — Corrected telemetry architecture proposal

### 3.1 Withdrawn recommendation (exact FU1 text)

FU1 §6.3 "Option A" + §6.4: add a nullable JSON field
`ExecutionEvidenceRecord.semantic_provenance` carrying the complete
`SemanticRuntimeResult.to_dict()` for SEMANTIC-stage records, recommended as
"the minimal, backward-compatible approach".

**Withdrawn.** Persisting the entire `to_dict()` into
`ExecutionEvidenceRecord.semantic_provenance` was recommended in FU1 without
the full consequences of what `to_dict()` contains or what the evidence
record's frozen contract is. The consequences:

**(a) `to_dict()` carries third-party page content and user input, not just
provenance.** `SemanticRuntimeResult.to_dict()` (runtime.py line 765) returns:
`case_id`, `target_mpn`, `target_description`, `candidate_title`,
`candidate_mpn_field`, `candidate_sku`, `candidate_specs`, `evidence_source`,
`prompt_version`, `requested_primary_provider`, `requested_primary_model`,
`attempts` (list of `{provider, model, status, latency_ms}`), `attempt_count`,
`fallback_used`, `fallback_reason`, `actual_provider`, `actual_model`,
`decision`, `confidence`, `matched_attributes`, `conflicting_attributes`,
`missing_critical_attributes`, `reason_code`, `error_type`.
The `candidate_*` fields are **extracted vendor page content** (title, MPN
field, SKU, specs) and `target_description` is free user input. That content
is already persisted as page/listing evidence from the FETCH/EXTRACT/NORMALIZE
stages (the whole point of the evidence-first design); duplicating it into a
new, unvalidated JSON column in the *execution evidence* table creates a
second, uncontrolled copy of market content with no codec, no version, and no
reader contract.

**(b) It changes the semantics of a frozen evidence artifact.**
`ExecutionEvidenceRecord` is defined as "one execution attempt … records the
outcome" with a **controlled vocabulary** `detail_code` ("never raw exception
text", `domain/evidence.py` lines 96–118), a strict writer
(`append_execution_attempt`, evidence_writer.py line 316) that validates
against `_VALID_COMBINATIONS` (line 139), and a strict reader
(`read_execution_evidence`, line 411) that fails closed on corruption. The
frozen tests pin exactly this: `tests/execution/test_4c_b_corrective_pass.py`
(`TestStrictEvidenceReaderImpossibleCombinations` line 595,
`TestLegalCombinationTable` line 668, `TestStrictEvidenceWriterMalformedUrl`
line 1012), `tests/execution/test_execution_orchestration.py`
(`test_unknown_detail_code_fails_closed` line 282). Turning one of these
records into an unstructured JSON payload carrier is an **established-evidence-
contract change**, not an "additive" one: the record's value is that every
field is bounded and machine-validated.

**(c) It would freeze `to_dict()`'s shape as a storage contract.**
`SemanticRuntimeResult` is a frozen dataclass whose `to_dict()` is pinned by
`tests/execution/test_semantic_integration.py::TestSafeProvenanceOnly::
test_semantic_result_contains_no_raw_output` (line 1008, which asserts the
dict contains `decision`/`confidence` and no raw/body/key fields). Persisting
the whole dict would make that in-memory shape a durability contract for all
historical and future runs.

The genuine gap FU1 identified — **per-attempt latency, provider/model, and
status are computed but lost after execution** (Section 1.5 above) — remains
real. What is withdrawn is the *shape* of the proposed fix, not the gap.

### 3.2 The approved V1 surface (inspected, production SHA)

- `SemanticAttempt` — frozen dataclass, `runtime.py` line 387: `provider`
  (non-empty str), `model` (non-empty str), `status`
  (`SemanticAttemptStatus`, 20 members), `latency_ms` (finite, ≥ 0).
  `to_dict()` line 421.
- `SemanticRuntimeResult` — frozen dataclass, line 453; 23 fields including
  the content fields named in 3.1(a); `to_dict()` line 765.
- `ExecutionEvidenceRecord` — `runs/models.py` line 488; 7 fields;
  `Meta` constraints: unique `(run, attempt_number)`,
  `attempt_number >= 1`, `candidate_url` empty-or-`^https?://`; indexes on
  `(run, attempt_number)`, `(run, stage)`, `(run, outcome)`.
- `ExecutionEvidenceWriter` — `evidence_writer.py` line 211; single write
  method `append_execution_attempt(stage, outcome, candidate_url="",
  detail_code=None)` (line 316); contiguous attempt numbers assigned only
  after successful INSERT.
- Strict evidence reader — `read_execution_evidence` (line 411); fails closed
  (`ExecutionEvidenceCorruptionError`) on non-contiguous numbering, unknown
  stage/outcome/detail, unsafe URLs, illegal combinations.
- Frozen boundary tests — `tests/semantic/test_runtime.py` (route pinning,
  fallback allowlist, per-attempt provenance, safe-latency on unconfigured
  transport), `tests/execution/test_semantic_integration.py` (eligibility,
  provenance validation, safe-provenance-only, deterministic authority),
  `tests/execution/test_4c_b_corrective_pass.py` (writer/reader strictness).
- Consumer note: at the production SHA, `read_execution_evidence` has **no
  production-code consumer** outside tests (verified by repository-wide
  search); the SEMANTIC-stage records are currently written
  (`semantic_integration.py` lines 349, 357) and read by no runtime path.

### 3.3 Alternative A — Bounded structured diagnostic logging (no DB migration)

**Idea:** emit the bounded per-attempt telemetry to the standard logging
facility at the **integration boundary** (`evaluate_semantic_matches`,
`semantic_integration.py` line 304, where the full `SemanticRuntimeResult` is
already in hand), leaving the frozen runtime and evidence contract untouched.
WinSW already captures process stderr into the service log; the runtime's
three existing `logger.warning` lines (runtime.py lines 1108, 1127, 1154)
already reach that log.

| Dimension | Assessment |
|---|---|
| Exact data fields | Per attempt: `run_id`, `case_id`, `seq` (1/2), `provider`, `model`, `status` (one of the 20 frozen `SemanticAttemptStatus` values), `latency_ms` (finite ≥ 0, already validated). Per result: `fallback_used` (bool), `fallback_reason` (frozen `SemanticRuntimeFallbackReason` or null), `error_type` (frozen `SemanticRuntimeErrorType` or null), `decision` (frozen `SemanticDecision` or null), `prompt_version` (constant). **Excluded by allowlist:** all content fields (`target_description`, `candidate_title`, `candidate_mpn_field`, `candidate_sku`, `candidate_specs`), URLs, raw output, exception text, token usage, keys. |
| Validation requirements | Reuse the frozen enums — no new vocabulary. One log record per attempt + one per result, key=value or single-line JSON. A test-scanned whitelist (AST/grep guard in the style of the existing architecture guard tests) pins that no excluded field name ever appears in a log call site. Latency finiteness is already enforced by `SemanticAttempt.__post_init__`. |
| Privacy/security implications | Lowest of the two alternatives: content never leaves the server's log files; the existing logs already contain `case_id` (8-char URL hash prefix — no URL-opacity weakening) and status names; the pilot_check precedent ("No API keys, endpoint URLs, or credentials appear in output", `runs/management/commands/pilot_check.py` line 205) applies verbatim. Residual: log files are readable by the service account's administrators; retention is bounded by WinSW log rotation. |
| Correlation to ResearchRun | `run_id` appears in the log line. Note: the frozen runtime's `evaluate()` does not receive a `run_id` (it receives `case_id`); the integration layer has both, so correlation happens there — no runtime signature change. Cross-check against persisted SEMANTIC evidence rows remains available via the FU1 §3.7 hash-prefix method. |
| Historical compatibility | Logs exist only from the change forward; no historical record is altered or reinterpreted; replay of old runs is unaffected. |
| Database migration impact | **None.** No model, no migration, `makemigrations --check` stays clean. |
| Required regression tests | (1) caplog tests over `evaluate_semantic_matches` for the three routing paths (primary-only success; fallback success; both-fail) asserting the exact bounded field set; (2) a negative guard test asserting no excluded field name / URL / raw content appears in captured logs; (3) existing frozen suites unchanged and green (runtime, integration, evidence writer/reader, architecture guards). |
| Established evidence/authority contract changes | **None.** `ExecutionEvidenceRecord`, its vocabularies, the strict reader, the frozen runtime, and pricing/identity authority are untouched. The new surface is operational diagnostic output, explicitly non-evidentiary. |
| Limitations | Not queryable per-run in the database; evidence is lost when log files rotate; a past incident's per-attempt detail is unrecoverable from logs alone once rotated. |

### 3.4 Alternative B — Minimal allowlisted, versioned per-attempt telemetry persistence

**Idea:** persist *only* the per-attempt provenance fields, under a versioned
shape, as a **new, separate** artifact — never as an unvalidated JSON blob on
`ExecutionEvidenceRecord`.

| Dimension | Assessment |
|---|---|
| Exact data fields (v1 allowlist) | `telemetry_schema_version` (int, =1); per attempt `seq` (1 or 2), `provider` (str), `model` (str), `status` (frozen status vocabulary), `latency_ms` (finite ≥ 0); per result `fallback_used` (bool), `fallback_reason` (frozen vocabulary or null), `error_type` (frozen vocabulary or null), `decision` (frozen vocabulary or null), `prompt_version` (str constant). **Excluded:** all content fields, URLs, token usage, raw output, exception text. (The allowlist is exactly `SemanticAttempt`'s fields + the routing/outcome fields — i.e. what `SemanticRuntimeResult` carries *about the execution*, not about the candidate.) |
| Validation requirements | A new frozen dataclass + validator in the `SemanticAttempt.__post_init__` style (strict types, finite latency, enum membership, exactly 1–2 attempts consistent with `fallback_used`). A versioned decoder that fails closed on unknown `telemetry_schema_version` (the `PriceIntelligenceSnapshot` versioned-codec precedent, FU3A/FU3B). Writer rejects anything outside the allowlist by construction (no dict pass-through). |
| Privacy/security implications | Bounded vocabularies + numerics + provider/model identifiers only; no new content class enters the DB (provider/model identifiers are already persisted for MATCH outcomes in `AiAssistedReviewCandidate`). Same non-leak discipline as A; additionally the data becomes durable and DB-permission-readable by anyone with database access. |
| Correlation to ResearchRun | FK to `ResearchRun` (same pattern as `ExecutionEvidenceRecord.run`); optionally a `(run, attempt_number)` link to the corresponding SEMANTIC evidence row for 1:1 correlation. |
| Historical compatibility | Historical runs simply have no telemetry rows; readers treat absence as "pre-telemetry". No reinterpretation of existing evidence. |
| Database migration impact | **One additive migration, new table** (recommended shape B1: e.g. `SemanticAttemptTelemetry(run FK, evidence_record FK or (run, attempt_number) link, seq, provider, model, status, latency_ms, fallback_used, fallback_reason, error_type, decision, prompt_version, telemetry_schema_version, created_at)`). Additive-only, nullable-free by construction, no data migration. SQLite pilot: low risk but non-zero (upgrade requires the runbook §H stop-and-backup step). The withdrawn FU1 shape (B2: JSON column on `ExecutionEvidenceRecord`) is **not** acceptable: it is a contract change to a frozen artifact (3.1(b)) and its strict reader would either ignore the blob (silent) or need weakening (forbidden). |
| Required regression tests | (1) model/migration tests (`makemigrations --check` clean after; new table round-trip); (2) strict writer + strict reader for the new artifact (vocabulary pins, attempt-count consistency, version fail-closed); (3) firewall test: telemetry is **not** consulted by any pricing/identity/replay authority path (precedent: the semantic firewall suites in `tests/evaluation/semantic_v2/`); (4) all frozen legacy suites unchanged and green. |
| Established evidence/authority contract changes | **Yes, by design** — a new persisted diagnostic artifact class enters the execution-evidence family. The production SHA's own phase naming ("…evidence-only exclusion investigation", `cde2a80`) shows the project is actively policing what counts as evidence; this new class must be explicitly classified *diagnostic, non-authority* in PLAN/STATUS and in any public replay surface. That classification work is a design/phase obligation, not an implementation detail. |
| Limitations | Schema surface area; upgrade/rollback procedure for the pilot DB; permanent retention of per-attempt data (acceptable, but it is a policy decision). |

### 3.5 Comparison and posture

| | A (bounded logging) | B (allowlisted versioned persistence) |
|---|---|---|
| Closes the per-attempt latency/provider/status gap | Yes (from deployment forward) | Yes (durable) |
| DB migration | None | One additive table |
| Frozen contract changes | None | New evidence-family artifact (diagnostic classification required) |
| Survives log rotation | No | Yes |
| Queryable per run | No | Yes |
| Risk to evidence/authority invariants | None | Low, but requires firewall tests + design phase |

**Neither option is implemented, and neither is recommended yet.** The
correct sequencing is set by Task 3: the likely root cause of the production
symptom (ambient proxy routing, Section 2.5) is an **operational** condition
that no telemetry design addresses. If Section 4's reads show a proxy input in
the service environment, the failure is explainable and fixable without any
code change, and the telemetry decision can be made with real data in hand.
If the proxy inputs are all absent, per-attempt `status`/`latency_ms` (option
A, cheapest) will discriminate DNS vs refused vs upstream-stall before any
schema is proposed. Option B remains the stronger long-term candidate *if*
durable per-run telemetry is approved after diagnosis.

### 3.6 Compliance

No code, tests, migrations, or configuration were modified; no option was
implemented.

---

## 4. Task 3 — Recommended next action: diagnose the service environment first

**Priority: establish what proxy inputs (and which connectivity condition)
the running `ProductIntelligencePilot` service actually has, using CMD-only,
read-only commands on the production machine, before any telemetry
implementation.**

### 4.1 Why this comes first

- The corrected proxy analysis (Section 2) makes ambient proxy routing a
  **live, unproven** root-cause hypothesis for the semantic
  `CONNECTION_ERROR`/`TIMEOUT` failures — and the hypothesis is decidable
  with four read-only inputs (D4–D7) without touching the service.
- The transport asymmetry (Section 2.6) predicts an observable fingerprint
  (semantic calls fail, vendor lookup times out on a *direct* path, 3A page
  fetches — which build a no-proxy opener — succeed), which the diagnosis
  confirms or refutes.
- Any telemetry work (Section 3) is more valuable after we know what the
  per-attempt data must distinguish (proxy vs DNS vs firewall vs upstream).

### 4.2 Interactive CMD vs the running service's effective environment

A `set` in an interactive CMD shows **that session's** environment only. The
service process's effective environment is assembled at **service start**
from:

1. **Machine (system) environment** — `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment`;
2. **The service account's user environment** — its `HKU\<SID>\Environment`
   (for LocalSystem/NetworkService: built-in, effectively empty user env; for
   a named account: that account's user variables);
3. **WinSW XML `<environment>` `<variable>` entries** — injected by WinSW into
   the process it starts;
4. Plus, at **request time** (not start time), urllib's own discovery: any
   `*_proxy` variable in (1)–(3), else the WinINET registry key of the
   **service account's** user hive (Section 2.3(b)).

Therefore: an interactive `set HTTP_PROXY` proves nothing about the service;
and a proxy variable visible interactively may or may not exist in the
service. The reads below target (1)–(3) and the service account's WinINET key
directly, all read-only.

### 4.3 CMD-only read-only diagnostic sequence (production machine)

Paths assume the FU1-recorded layout (`C:\Product_Intelligence`, WinSW under
`C:\Product_Intelligence\win-sw`); adjust if the actual install path differs.
**Report discipline: never paste `*_API_KEY*` values, base-URL values (the
vLLM host is a private endpoint), or proxy-server values into the report —
record presence/absence, booleans, and ports only.**

**D1. Service state and PID**

```cmd
sc queryex ProductIntelligencePilot
```
Record: STATE (RUNNING?), PID, SERVICE_START_NAME (the service account).

**D2. Confirm the process and its account**

```cmd
tasklist /v /fi "PID eq <PID from D1>"
```
Record: image name (`python.exe`), User Name, Session.

**D3. Waitress liveness (no HTTP, no TLS — raw TCP connect to loopback only)**

```cmd
netstat -an | findstr :8080
C:\Product_Intelligence\.venv\Scripts\python -c "import socket; s=socket.create_connection(('127.0.0.1',8080),5); print('TCP 8080 OK'); s.close()"
```
A listening `127.0.0.1:8080`/`0.0.0.0:8080` plus a successful TCP connect
confirms the web layer is up without issuing any request.

**D4. WinSW environment injection (presence only)**

```cmd
type C:\Product_Intelligence\win-sw\ProductIntelligencePilot.xml
```
Record for each `<variable name=...>`: the **name** only. Flag presence/absence
of: `HTTP_PROXY`, `http_proxy`, `HTTPS_PROXY`, `https_proxy`, `NO_PROXY`,
`no_proxy`, and the `PI_SEMANTIC_*` configuration names. **Do not record the
values of `PI_SEMANTIC_AMAX_API_KEY`, `PI_SEMANTIC_VLLM_262K_API_KEY`, or any
`*_BASE_URL`.**

**D5. Machine environment proxy variables**

```cmd
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v HTTP_PROXY
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v http_proxy
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v HTTPS_PROXY
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v https_proxy
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v NO_PROXY
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v no_proxy
```
`ERROR: ... not found` (or exit code ≠ 0) = unset. If present, record
**presence only** (and scheme/port, never host or credentials).

**D6. Service account user environment**

If D1 shows `LocalSystem` / `NetworkService`: user environment is built-in and
effectively empty — skip to D7. If a named account:

```cmd
wmic useraccount where "name='<account from D1>'" get sid
reg query "HKU\<SID from above>\Environment" /v HTTP_PROXY
reg query "HKU\<SID from above>\Environment" /v HTTPS_PROXY
reg query "HKU\<SID from above>\Environment" /v NO_PROXY
```
(the lowercase variants likewise). `HKU\<SID>` is queryable while the
service is running (its session-0 profile hive is loaded). If D1 shows a
domain account (`DOMAIN\name`), the local `wmic useraccount` lookup will not
find it — record the account name and mark D6 as not-evaluated rather than
resolving the SID by unapproved means; D4 + D5 + D7 (hive rule: `.DEFAULT`
for built-in accounts, the account's hive only if the SID is already known)
still bound the machine-side proxy inputs.

**D7. WinINET system proxy of the service account (the exact input of
`getproxies_registry`)**

Hive: `HKU\.DEFAULT` for LocalSystem, `HKU\<SID>` (D6) for a named account,
`HKU\.DEFAULT` for NetworkService (system account).

```cmd
reg query "HKU\<hive from above>\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable
reg query "HKU\<hive from above>\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer
```
Record: `ProxyEnable` value (0/1) and **whether** `ProxyServer` exists and is
non-empty — **not its value**. (Contrast, optional: the same two queries under
plain `HKCU` show the *interactive* operator's WinINET proxy — differences
between the two hives are themselves diagnostic.)

**D8. Interactive session (for the record, explicitly labeled as NOT the
service environment)**

```cmd
set HTTP_PROXY
set http_proxy
set HTTPS_PROXY
set https_proxy
set NO_PROXY
set no_proxy
```

**D9. Production interpreter version (brackets which stdlib code is running)**

```cmd
C:\Product_Intelligence\.venv\Scripts\python --version
```
The proxy mechanism verified for 3.11.9 and 3.14.7 (Section 2.3) covers 3.12;
record the actual version regardless.

**D10. Deployed-code identity (read-only; no service impact)**

On the production machine:

```cmd
C:\Product_Intelligence\.venv\Scripts\python -c "import hashlib; d=open(r'C:\Product_Intelligence\product_intelligence\semantic\transport.py','rb').read().replace(b'\r\n',b'\n'); print(hashlib.sha256(d).hexdigest())"
```
Compare against the value computed here from the production git blob
(CRLF-normalized):

| File (CRLF-normalized SHA-256 at `cde2a80`) | Value |
|---|---|
| `product_intelligence/semantic/transport.py` | `e4917ffe8b3a4d986ee30a1f8d47eb536f8fc7bae3fc233d0d1f1436d4d5e345` |
| `product_intelligence/semantic/runtime.py` | `f67ddfc6fddaaa21f9c538a76da3b75dc3d96b351f11872a61331668c76b8167` |
| `product_intelligence/execution/evidence_writer.py` | `e0b536314b75981b23f71286a20ce0e44d59d8a8136acb775dc2feb3eb8dffd8` |
| `product_intelligence/execution/semantic_integration.py` | `95ae11f6f6806c0222aa1ca167bced592f7651989c9b06aee2b81323bdeec14a` |
| `product_intelligence/runs/models.py` | `223d7fa956b909b1ae49f205691a5270edda1ff107cd9938720d50b552f78bc6` |

A mismatch means the deployed tree is not the analyzed SHA and every code
reference in this report must be re-verified before acting.

**D11. Endpoint reachability from the production host (no HTTP request, no
chat completion, no TLS, no paid call)**

Hostnames: read from the service's effective `PI_SEMANTIC_*_BASE_URL` on the
production machine (D4/D5/D6); **do not paste private hostnames into the
report** — label them `PRIMARY-HOST` / `FALLBACK-HOST`.

```cmd
nslookup PRIMARY-HOST
nslookup FALLBACK-HOST
C:\Product_Intelligence\.venv\Scripts\python -c "import socket; s=socket.create_connection(('PRIMARY-HOST',443),5); print('TCP 443 OK'); s.close()"
C:\Product_Intelligence\.venv\Scripts\python -c "import socket; s=socket.create_connection(('FALLBACK-HOST',443),5); print('TCP 443 OK'); s.close()"
```
A raw TCP connect proves route+firewall+port without sending an HTTP request.
`nslookup`/TCP failures distinguish DNS vs egress/firewall vs host-down.
(Ping/ICMP is inconclusive where firewalls drop ICMP; do not rely on it.)

**D12. Service log: bounded error census (read-only)**

```cmd
type C:\Product_Intelligence\win-sw\ProductIntelligencePilot-error.log | find /c "CONNECTION_ERROR"
type C:\Product_Intelligence\win-sw\ProductIntelligencePilot-error.log | find /c "TIMEOUT"
type C:\Product_Intelligence\win-sw\ProductIntelligencePilot-error.log | findstr "entering fallback"
```
Extract the `candidate-xxxxxxxx-N` case IDs from the warning lines and compare
their 8-char hash prefixes with the `candidate_url` values of the run's
persisted SEMANTIC evidence rows (FU1 §3.7 method). This attributes the
stderr warnings to the specific run without exposing full URLs.

**D13. (Optional — requires explicit approval) read-only evidence inspection**

`C:\Product_Intelligence\.venv\Scripts\python manage.py shell -c "..."` with
**SELECT-only** statements over the run's `ExecutionEvidenceRecord` rows. No
writes, no migrations, no `migrate`. If not approved, skip; D12's log census
plus the web report is sufficient.

### 4.4 Decision table (what the results mean)

| D4–D7 result | Interpretation |
|---|---|
| Any `*_proxy` variable present in service env (D4/D5/D6) | Ambient proxy **confirmed as effective** for the semantic transport (Section 2.3). Root-cause hypothesis for CONNECTION_ERROR/TIMEOUT established — verify against the *proxy host:port* recorded in D5/D7 with the same D11 TCP-connect pattern (never paste the proxy host into the report): proxy unreachable from the production host → the exact observed failure mode. Fix is operational (remove the variable from the service environment / add a `NO_PROXY` entry) — a **configuration decision for the owner**, outside this investigation's authority. |
| No env proxy, but D7 `ProxyEnable=1` + non-empty `ProxyServer` for the service account's hive | WinINET registry proxy **effective** (the env-empty branch of `getproxies()`). Same consequences as above. |
| No env proxy and D7 disabled/absent | `getproxies()` is empty in the service → semantic transport is proxy-less → **ambient proxy excluded** for that process. Differential: D11 DNS/egress/upstream; the vendor-lookup timeout then points at account-level egress/firewall (note the vendor adapter is *also* direct — Section 2.6 — so a common egress block hits vendor and semantic, while 3A fetches to public pages may still work if the block is host-specific). |
| D10 hash mismatch | Stop; deployed code ≠ analyzed SHA; re-baseline before any further diagnosis. |

### 4.5 Prohibited during this diagnosis

- No live chat completions, no paid model calls, no HTTP requests to provider
  endpoints (D11 is TCP-connect only; D3 is loopback-only).
- No configuration changes of any kind (no `setx`, no `netsh`, no WinSW XML
  edits, no registry writes, no environment edits).
- No service stop/start/restart (`sc stop/start`, `net stop/start`).
- No production DB writes (D13 is SELECT-only and requires approval).
- No code changes, no commits, no pushes.
- No printing of proxy URLs, credentials, API keys, or private endpoints in
  any report artifact.

---

## 5. Statement classification (of record)

**Accepted findings** (FU1, carried forward): Sections 1.1–1.11 above.

**Retracted claims** (FU1 → this correction):
1. FU1 §4.3 "KEY FINDING": "The V1 semantic transport does NOT install a proxy
   handler … Ambient HTTP_PROXY/HTTPS_PROXY environment variables are NOT used
   by this transport …" — **retracted** (Section 2.1/2.3: the default
   `ProxyHandler` is installed by `build_opener` and is effective whenever
   `getproxies()` is non-empty in the service process).
2. FU1 §4.3 evidence row: "NO proxy handler is installed, so ambient proxy env
   vars are ignored for the semantic transport … Neither semantic transport
   uses a proxy." — **retracted** (Section 2.1/2.6).
3. FU1 §6.3/§6.4: recommendation to persist the entire
   `SemanticRuntimeResult.to_dict()` into
   `ExecutionEvidenceRecord.semantic_provenance` as "the minimal,
   backward-compatible approach" — **withdrawn** (Section 3.1).
4. FU1 §2.2: "15 codes" for `PRIMARY_FALLBACK_ELIGIBLE_ERRORS` — **corrected**
   to 14 (Section 0).

**Unproven hypotheses** (remain unproven; Section 4 is the decider):
1. An ambient proxy (env or WinINET) is configured in the running WinSW
   service environment and caused the semantic `CONNECTION_ERROR`/`TIMEOUT`
   failures (now a live hypothesis — Section 2.5; was *excluded* by FU1's
   retracted claim).
2. The 21 stderr `CONNECTION_ERROR` warnings belong to the single Micron run
   (FU1 §3.4 stands: not definitively attributed; D12 provides the method).
3. Vendor-lookup timeout and semantic failures share a single root cause
   (Section 2.6's asymmetry makes "different exposure, possibly different
   cause" the working assumption).
4. Per-candidate model-call count in the 10–20 range for the Micron run
   (FU1 §3.4; only per-attempt telemetry — Section 3 — would close this).

**Recommended next action:** execute Section 4 (CMD-only, read-only) on the
production machine and report the D1–D12 results (with the report
discipline above). Only after that result: (a) if a proxy input is found —
the owner decides the operational fix; telemetry is re-scoped; (b) if no
proxy input is found — ambient proxy is excluded, and Alternative A of
Section 3.3 (bounded diagnostic logging, no migration) is the lowest-risk
telemetry step if ChatGPT approves it as a separate phase. No telemetry
implementation is authorized by this document.

---

## 6. Verification record and zero-modification attestation

**Worktree state (unchanged by this task):**
`git status --short` shows only the pre-existing ` M tmp_collection.txt` and
the pre-existing untracked files (V2 design docs, benchmark artifacts, INV1
report, FU1 correction, vendor-lookup test file). This document
(`docs/VENDOR_LOOKUP_FAILURE_INV1_FU2_CORRECTION.md`) is the only new file
created; all verification scripts were written to
`%TEMP%` (`fu2_urllib_proxy_verify.py`, `fu2_probe2.py`, `fu2_probe3.py`,
`fu2_dump.py`, `fu2_dump_311.txt`, `fu2_dump_314.txt`,
`fu2_loopback_demo.py`, `fu2_sources.py`), outside the repository. One
accidental redirect artifact inside the repo directory was created and
removed during this session; the final `git status` is as described above.

**Read-only code inspection:** all production references via
`git show cde2a80:<path>` (no worktree file was opened for production-code
reading, no checkout/restore/reset/stash/clean, no commit, no push).

**Stdlib verification (offline, no network):** Python 3.14.7 (repo venv) and
Python 3.11.9 (32-bit). `build_opener`, `OpenerDirector.add_handler`,
`ProxyHandler.__init__`, `getproxies`, `ProxyHandler.proxy_open`,
`proxy_bypass_environment` verified byte-identical across both interpreters,
bracketing the 3.12 production baseline. The routing experiment (Section
2.4) used only `127.0.0.1:9` (loopback, nothing listening) and
`*.invalid` (reserved, unresolvable) names — no external traffic. No proxy
values, keys, or private endpoints were printed at any point.

**Regression tests (exact):** no code was modified; the relevant frozen
boundary suites were run on the unmodified worktree as a sanity check —
`pytest tests/semantic/test_runtime.py
tests/execution/test_4c_b_corrective_pass.py
tests/execution/test_semantic_integration.py` → **291 passed, 0 failed,
0 errors, 0 skipped, exit 0 (0.98 s)**.

---

## Final State

**FU2 CORRECTION COMPLETE — PENDING CHATGPT REVIEW**

This investigation makes NO implementation changes: no production code,
tests, migrations, or configuration modified; no commits/pushes; no
destructive Git operations; no live model calls; no service interaction.
It does NOT declare APPROVED, FIXED, or FROZEN. ChatGPT retains final
architecture and approval authority.
