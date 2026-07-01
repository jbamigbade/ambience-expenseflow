# 🧪 Evaluation Showcase, Test Harness & Compliance Logging
**Track**: Agents for Business

This document showcases the verification and evaluation workflows of **Ambience ExpenseFlow**. Ensuring absolute compliance in an enterprise financial application requires a multi-layered testing strategy combining local unit tests, integration harnesses, and LLM-as-a-judge evaluation datasets.

---

## 1. Multi-Tiered Testing Strategy

To guarantee the reliability of our automated policy engines and receipt parsers, we implement a three-tiered testing model:

```
                  +----------------------------------------------+
                  |           LLM Quality Evaluations            |
                  |     (google-adk[eval] & Gemini metrics)      |
                  +----------------------------------------------+
                                         |
                                         v
                  +----------------------------------------------+
                  |         E2E Integration Test Suite           |
                  |  (Authenticates, submits & audits via APIs)   |
                  +----------------------------------------------+
                                         |
                                         v
                  +----------------------------------------------+
                  |            Core Rule Unit Tests              |
                  |     (Asserts math, rates, and per diems)     |
                  +----------------------------------------------+
```

---

## 2. Evidence of Passing Test Harnesses

Our repository includes 38 rigorous unit and integration tests, achieving comprehensive coverage over claim drafting, state progression, and manager override loops.

### Test Execution Proof
Running the test suite yields clean completion across all modules:
```bash
$ uv run pytest tests/
================================== test session starts ===================================
platform win32 -- Python 3.11.4, pytest-9.0.2, pluggy-1.4.0
collected 38 items

tests/unit/test_dashboard_auth.py .....................                            [ 55%]
tests/unit/test_expense_reports_workflow.py .................                      [100%]

============================= 38 passed, 123 warnings in 28.78s ============================
```

### Core Areas Validated
1. **Compliance Mathematics**: Asserts that mileage calculations correctly evaluate at $0.67/mile and flag any discrepancies.
2. **Per Diem Bounds**: Verifies that localized per diem allowances are queried correctly and flag claims exceeding daily caps.
3. **Role-Based Routing**: Asserts that unauthenticated actors cannot access `/api/pending` and only authenticated Managers can hit `/api/override`.
4. **Draft Report Compiling**: Validates that draft reports can span multiple weeks, letting employees add, edit, and delete claims dynamically before submission.

---

## 3. Generative Quality Evaluations (ADK Eval)

For the LLM-driven components (receipt parsing and recommendation engine), standard unit tests are insufficient. We utilize the `google-adk[eval]` optional dependencies to evaluate model changes.

### Synthetic Evaluation Datasets
We compile evaluation sets representing real-world travel claims, detailing the original invoice and the target extraction fields.
* **Sample Evaluation Row**:
  ```json
  {
    "input_receipt_gcs": "gcs://receipts_bucket/dinner_receipt_raw.jpg",
    "expected_merchant": "The Prime Steakhouse",
    "expected_amount": 128.50,
    "expected_date": "2026-06-21",
    "corporate_limit_meals": 100.00,
    "expected_status": "FLAGGED_POLICY_EXCEPTION"
  }
  ```

### Key LLM Quality Metrics Measured
* **Entity Extraction F1-Score**: Evaluates accuracy in extracting key-value pairs (dates, totals, vendors).
* **Policy Recommendation Accuracy**: Measures how reliably Gemini correctly identifies whether an extracted claim breaches corporate policy.
* **Latency (p95)**: Tracks the time elapsed for LLM completion to ensure asynchronous Pub/Sub routines complete within acceptable thresholds (under 5 seconds).

---

## 4. Immutable Auditing Ledger

The Firestore database acts as our production ledger, compiling chronological timelines of user and agent operations.

### Data Structure Schema
Every parent report document contains an `audit_timeline` subcollection. The entries are immutable and structured to record every manual or automated adjustment:

```json
{
  "report_id": "rep_90182_a",
  "audit_timeline": [
    {
      "timestamp": "2026-06-23T04:12:01.902Z",
      "actor_email": "employee_traveler@company.com",
      "action": "DRAFT_REPORT_CREATED",
      "details": "Draft established for travel week commencing 2026-06-15"
    },
    {
      "timestamp": "2026-06-23T04:15:22.110Z",
      "actor_email": "vertex_ai_agent_runtime",
      "action": "RECEIPT_EXTRACTED_AND_CHECKED",
      "details": "Parsed dinner receipt of $128.50. Flagged exception: exceeds meal daily allowance cap of $100.00."
    },
    {
      "timestamp": "2026-06-23T04:18:45.305Z",
      "actor_email": "obamigbade@gmail.com",
      "action": "MANAGER_OVERRIDE_APPROVED",
      "details": "Override authorized. Justification: 'Client dinner with vice president of procurement. Approved per contract terms.'"
    }
  ]
}
```

This ledger is non-editable. No client or API has mutation access to existing timeline objects, establishing a fully compliant corporate paper trail that is immediately ready for financial audit checks.
