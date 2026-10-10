# Semantic V2 Qualification Report (Q3-A offline)

- **Model under qualification:** `vllm-262k/Qwen3.6-27B-262K` (route role: FALLBACK)
- **Corpus:** `PI-SEMANTIC-V2-QUALIFICATION` v1.1.0 (digest `14396eae884841e20063cb4da0d4424ce8f05ff8745f2c787fc395d250ea8dcd`)
- **Frozen contract:** semantic `V2`, prompt `2.1`, input schema `1`, output schema `1`, authority `SEMANTIC_AUTHORITY_V2_S2A_FU3`; system prompt digest `e2949e7544d26228ac6f5555ae8ebd28019076e1de88ace25e79a5d942d818fc`
- **Decision:** `POLICY_PENDING` — COVERAGE:not_captured=43,not_invoked=0,runtime_failures=0,capture_integrity_failures=0,contract_violations=0, POLICY_PENDING:no approved applicable policy

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

## Authority

- Authority granted: **False**; V2_AUTHORITY_QUALIFIED marker: False
- this report is evaluation evidence only; it grants no pricing authority, no tier promotion, and no human-review behavior change

- Report digest: `9b00fc94717afe7bac8f5357ebba9949d02eaa1686ccaec1ee7379ba3c74b2c6` (generated 2026-10-08T00:00:00Z)
