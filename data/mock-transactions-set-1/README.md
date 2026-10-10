# Mock Transaction Data — Smart Retry Engine

Self-contained mock data set for the **Smart Retry Engine**, derived from the E2E
scenario suite in [`tests/e2e/`](../../tests/e2e/). Each JSON file describes one
scenario: the **mock bank state** to seed, the full **request payload(s)** for
`POST /retry-decision`, and the **expected response contract**.

Intended use: share these as the expected input/output behaviour of the system
(demo scripts, stakeholder walkthroughs, regression baselines).

## File format

Every scenario file follows the same shape:

```jsonc
{
  "scenario_id":   "E1",                    // stable id matching the test suite
  "name":          "...",                   // human-readable title
  "category":      "network-failure",       // grouping tag
  "description":   "...",                   // what happens & why
  "mock_bank_state": {                      // state to seed in the mock bank API
    "bank_status":   { "<BIC>": { "bank_status": "ONLINE|DEGRADED|DOWN", "estimated_recovery": null } },
    "accounts":      { "<IBAN>": { "exists": true, "status": "ACTIVE|INACTIVE|FROZEN|CLOSED|NOT_FOUND", "account_name": "...", "currency": "..." } },
    "balances":      { "<IBAN>": { "current": 0.0, "available": 0.0 } },
    "fault_injection": null                 // e.g. { "forced_status_code": 503 }
  },
  "config":        { ... },                 // optional engine config (max_retry_count, max_agent_loops)
  "api_requests": [                         // one or more api_request entries
    {
      "label":       "...",                 // optional tag (e.g. "below_limit")
      "request":     { /* full POST /retry-decision body */ },
      "expected_http_status": 200,          // expected HTTP status code
      "expected_response": {                // concrete RetryRecommendationResponse body
        "transaction_id":       "...",      // echoes the request's transaction_id
        "recommendation":       "RETRY_NOW",// single enum value
        "confidence_score":     0.9,        // concrete float in [0, 1]
        "explanation":          "...",      // realistic sample explanation
        "optimal_timing":       null,       // date-time string when RETRY_LATER, else null
        "correction_suggestions": null      // string array when RETRY_AFTER_UPDATE, else null
      },
      "notes":       "..."                  // acceptance criteria / rationale for this pair
    }
  ]
}
```

### Response conventions

Each `response` object is a **concrete example** of a valid
[`RetryRecommendationResponse`](../../src/api_gateway/schemas.py) body — the kind
of output you would expect the system to produce for that scenario. Because the
decision is produced by an LLM agent, the exact wording of `explanation` and the
precise `confidence_score` will vary between runs; treat them as representative
samples rather than byte-for-byte assertions. The `notes` field on each request
pair documents the acceptance criteria (e.g. "confidence must be ≥ 0.7",
"suggestions must reference the IBAN").

Field rules per recommendation value:

| Recommendation | `optimal_timing` | `correction_suggestions` |
|---|---|---|
| `RETRY_NOW` | `null` | `null` |
| `RETRY_LATER` | ISO-8601 date-time (required) | `null` |
| `RETRY_AFTER_UPDATE` | `null` | non-empty string array (required) |
| `DONT_RETRY` | `null` | `null` |
| `NO_RECOMMENDATION` | `null` | `null` |

Request bodies conform to [`RetryRecommendationRequest`](../../src/api_gateway/schemas.py);
responses to [`RetryRecommendationResponse`](../../src/api_gateway/schemas.py).
Mock bank endpoints follow [`docs/contracts/bank_status_api.yaml`](../contracts/bank_status_api.yaml).

## Scenario index

### Network failures

| File | ID | Failure code | Bank state | Expected recommendation |
|---|---|---|---|---|
| [`e1-network-timeout.json`](e1-network-timeout.json) | E1 | `NETWORK_TIMEOUT` | ONLINE | RETRY_NOW, confidence ≥ 0.7 |
| [`e2-bank-outage-repeated-failures.json`](e2-bank-outage-repeated-failures.json) | E2 | `GATEWAY_TIMEOUT` | DOWN | RETRY_LATER + optimal_timing (×2 retries) |
| [`e9-bank-down-estimated-recovery.json`](e9-bank-down-estimated-recovery.json) | E9 | `GATEWAY_TIMEOUT` | DOWN + recovery ETA | RETRY_LATER, timing ≥ recovery window |

### Healthy / nominal

| File | ID | Failure code | Bank state | Expected recommendation |
|---|---|---|---|---|
| [`e5-healthy-processing-glitch.json`](e5-healthy-processing-glitch.json) | E5 | `PROCESSING_ERROR` | ONLINE, ACTIVE, funded | RETRY_NOW, confidence ≥ 0.7 |

### Account failures

| File | ID | Failure code | Account state | Expected recommendation |
|---|---|---|---|---|
| [`e3-invalid-beneficiary-account.json`](e3-invalid-beneficiary-account.json) | E3 | `INVALID_ACCOUNT` | NOT_FOUND | RETRY_AFTER_UPDATE + suggestions |
| [`e3c-iban-with-spaces.json`](e3c-iban-with-spaces.json) | E3C | `INVALID_ACCOUNT` | spaced IBAN → NOT_FOUND; clean → ACTIVE | RETRY_AFTER_UPDATE (strip spaces) |
| [`e4-frozen-account-insufficient-funds.json`](e4-frozen-account-insufficient-funds.json) | E4 | `INSUFFICIENT_FUNDS` | FROZEN | RETRY_AFTER_UPDATE + suggestions |
| [`e10-closed-beneficiary-account.json`](e10-closed-beneficiary-account.json) | E10 | `ACCOUNT_CLOSED` | CLOSED | RETRY_AFTER_UPDATE or DONT_RETRY |

### Name mismatches (incl. Arabic & fuzzy logic)

| File | ID | Submitted name | Registered name | Match type | Expected |
|---|---|---|---|---|---|
| [`e11-arabic-name-transliteration-match.json`](e11-arabic-name-transliteration-match.json) | E11 | `شركة الأمل للتجارة` | Al-Amal Trading Co. | Arabic ↔ transliteration, **same entity** | RETRY_AFTER_UPDATE |
| [`e12-arabic-name-transliteration-mismatch.json`](e12-arabic-name-transliteration-mismatch.json) | E12 | `شركة الأمل للتجارة` | Al-Hope Trading LLC | Arabic ↔ transliteration, **different entity** | RETRY_AFTER_UPDATE (verify name) |
| [`e13-name-punctuation-abbreviation.json`](e13-name-punctuation-abbreviation.json) | E13 | Al-Amal Trading Co. | Al Amal Trading Company | punctuation / abbreviation | RETRY_AFTER_UPDATE |
| [`e14-name-word-order.json`](e14-name-word-order.json) | E14 | Trading Al-Amal International | Al-Amal International Trading | word order | RETRY_AFTER_UPDATE |
| [`e15-name-case-difference.json`](e15-name-case-difference.json) | E15 | AL-AMAL TRADING CO. | Al-Amal Trading Co. | letter case | RETRY_AFTER_UPDATE |

### Retry limit (circuit breaker, `max_retry_count = 3`)

| File | ID | retry_count | Expected |
|---|---|---|---|
| [`e6-retry-count-max-circuit-breaker.json`](e6-retry-count-max-circuit-breaker.json) | E6 | 2 / 3 / 5 | 200 (agent) / 429 DONT_RETRY conf 1.0 / 429 DONT_RETRY |
| [`c5-retry-count-exceeds-max.json`](c5-retry-count-exceeds-max.json) | C5 | 10 | 429 DONT_RETRY, confidence exactly 1.0 |

### Resilience

| File | ID | Fault | Expected |
|---|---|---|---|
| [`e8-persistent-api-failure-loop-exhaustion.json`](e8-persistent-api-failure-loop-exhaustion.json) | E8 | all bank APIs → 503 | NO_RECOMMENDATION, confidence < 0.5, no correction suggestions |

## Notes

- **Parties:** the ordering customer (`Globex Manufacturing Ltd`,
  `DE02120300000000202051`, BIC `COBADEFFXXX`) is always distinct from the
  beneficiary in every scenario.
- **Non-determinism:** the `explanation` text and exact `confidence_score` will
  vary between LLM runs; the values shown are representative samples. Use the
  `notes` field for the actual acceptance criteria.
- **Deterministic paths:** circuit-breaker (E6/C5) and loop-exhaustion (E8)
  responses are fully deterministic — `recommendation`, `confidence_score`, and
  the key phrase in `explanation` ("Max retry limit reached" / "Unable to
  produce a recommendation") are stable across runs.
- **Seeding:** `mock_bank_state` maps 1:1 onto the configuration helpers of
  [`MockBankAPI`](../../tests/fixtures/mock_bank_api.py) (`set_bank_status`,
  `set_account`, `set_balance`, `set_forced_status`).
- **Defaults:** any BIC/IBAN not listed in `mock_bank_state` falls back to the
  mock's defaults (bank ONLINE, account exists/ACTIVE, balance 10000/9500).
