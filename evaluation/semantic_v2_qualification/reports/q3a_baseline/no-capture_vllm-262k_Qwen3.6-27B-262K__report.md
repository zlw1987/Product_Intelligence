# Semantic V2 Qualification Report (Q3-A offline)

- **Model under qualification:** `vllm-262k/Qwen3.6-27B-262K` (route role: FALLBACK)
- **Corpus:** `PI-SEMANTIC-V2-QUALIFICATION` v1.0.0 (digest `2c37ba088c317d8cefc6ad0dd7e0d73cfd085f6474ef43eb6953e3cf0170b549`)
- **Frozen contract:** semantic `V2`, prompt `2.0`, input schema `1`, output schema `1`, authority `SEMANTIC_AUTHORITY_V2_S2A_FU2`; system prompt digest `c0cc98bdd6d357e81d4692218f18d354351fc2833267b3062b7cd74b18445a84`
- **Decision:** `POLICY_PENDING` — COVERAGE:not_captured=43,not_invoked=0,runtime_failures=0,capture_integrity_failures=0,contract_violations=0, POLICY_PENDING:policy draft-1 is DRAFT, not approved

## Safety gates (mandatory, fail-closed)

| Gate | Passed | Failing cases |
| --- | --- | --- |
| zero_false_match_on_always_hard_conflicts | PASS | - |
| zero_false_match_on_packaging_quantity_conflicts | PASS | - |
| zero_false_match_on_accessory_product_role_conflicts | PASS | - |
| zero_schema_bypass_acceptance | PASS | - |
| zero_unauthorized_authority_promotion | PASS | - |
| zero_customer_alias_authority_promotion | PASS | - |
| zero_contract_version_mismatch | PASS | - |
| zero_missing_required_evaluation_silent_pass | PASS | - |

## Metrics

- Total cases: 56 (authoritative 36, ambiguous 7, contract-negative 13)
- Evaluated: 0; not captured: 43; runtime failures: 0 (none); capture integrity failures: 0; contract violations: 0
- Valid structured response rate: **unavailable** (denominator 0)
- MATCH precision (authoritative): **unavailable** (denominator 0)
- MATCH recall (authoritative): **unavailable** (denominator 0)
- NO_MATCH accuracy (authoritative): **unavailable** (denominator 0)
- UNCERTAIN rate (authoritative): **unavailable** (denominator 0)
- False MATCH: 0
- False NO_MATCH: 0
- HARD_CONFLICT false MATCH: 0
- Packaging/bundle false MATCH: 0
- Accessory/product-role false MATCH: 0
- Near-miss false MATCH: 0
- Sales-unit-safety false MATCH: 0
- Severity counts: {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'REVIEW': 0} (model confidence never overrides the independent label)
- Ambiguous cases (visible, excluded from hard accuracy): 0 defensible / 0 outside the defensible set of 7 total

### Performance by substate

| Substate | Total | Evaluated | Correct | False MATCH | False NO_MATCH | Runtime failure | Not captured | Not invoked |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U1_TITLE_MPN | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 0 |
| U2_SKU_ONLY | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 0 |
| U3_PARTIAL_BOUNDARY | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| U4_NO_MPN | 18 | 0 | 0 | 0 | 0 | 0 | 18 | 0 |
| U5_NEAR_MISS_MPN | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |

### Performance by category

| Category | Total | Evaluated | Correct | False MATCH | False NO_MATCH | Runtime failure | Not captured | Not invoked |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| enterprise_ssd | 32 | 0 | 0 | 0 | 0 | 0 | 32 | 0 |
| network_adapter | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| processor | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| server_memory | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 |
| workstation_gpu | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |

## Qualification policy

- Policy: `PI-SEMANTIC-V2-QUALIFICATION-POLICY` vdraft-1 — **DRAFT**
- DRAFT proposal - not a finalized production acceptance threshold; qualification requires an approved policy
- match_precision_min: bound >= 0.990000, value unavailable — indeterminate
- match_recall_min: bound >= 0.900000, value unavailable — indeterminate
- valid_structured_response_rate_min: bound >= 0.990000, value unavailable — indeterminate
- eligible_coverage_min: bound >= 1.000000, value 0.000000 — NOT met

## Authority

- Authority granted: **False**; V2_AUTHORITY_QUALIFIED marker: False
- this report is evaluation evidence only; it grants no pricing authority, no tier promotion, and no human-review behavior change

- Report digest: `54a7550f385025981813360c1ac2d8833d220ba246de05589bebf95fe4ba1dd9` (generated 2026-10-08T00:00:00Z)
