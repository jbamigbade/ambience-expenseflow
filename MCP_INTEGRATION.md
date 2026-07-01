# 🔌 Model Context Protocol (MCP) & Custom Agent Skills
**Track**: Agents for Business

This document details how **Ambience ExpenseFlow** integrates the Model Context Protocol (MCP) and custom agent skills to supply the Gemini reasoning model with enterprise compliance guidelines, automated calculations, and secure data-retrieval mechanisms.

---

## 1. Model Context Protocol (MCP) Integration

To prevent hallucinations and guarantee absolute adherence to corporate guidelines, the Vertex AI Agent Runtime uses the **Model Context Protocol (MCP)**. This client-server architecture decouples the reasoning engine (Gemini) from the underlying enterprise systems, exposing tools, documents, and resources via a clean, unified protocol.

### Why MCP?
1. **Dynamic Context Injection**: Rather than training the LLM on corporate handbooks, the model queries live compliance documents on-demand.
2. **Standardized Tool Access**: Exposes calculations (e.g., federal mileage computing, per diem boundaries) as executable tools with strict JSON-schema contracts.
3. **Decoupled Architecture**: Corporate policies or database backends can change independently without requiring retraining or redeployment of the reasoning model.

### Communication Flow
* **Transport Protocol**: stdio (or SSE) for communication between the Vertex AI Reasoning Engine host (MCP client) and the MCP servers.
* **Knowledge Retrieval**: Built-in lazy-loaded MCP tools, such as the `google-developer-knowledge` server, allow the model to execute semantic search queries across corporate travel guidelines, and regulatory PDF reference indices.

---

## 2. Configured Agent Skills & Tool Declarations

The reasoning model in Ambience ExpenseFlow is equipped with three primary custom agent skills, defined as Python tools under the `app/` directory and managed via the ADK manifest (`agents-cli-manifest.yaml`):

### 1. `get_corporate_per_diem(location: str, category: str) -> float`
Queries the configurable Firestore backend to retrieve the active daily allowance limit for a given location and category.
* **Schema Target**:
  ```json
  {
    "type": "object",
    "properties": {
      "location": { "type": "string", "description": "The travel city or country" },
      "category": { "type": "string", "enum": ["meals", "lodging", "transportation"] }
    },
    "required": ["location", "category"]
  }
  ```
* **Behavior**: Returns the local limit (e.g., meals in Washington D.C. = $120.00/day). If the category claim exceeds this limit, the model flags it as `FLAGGED_POLICY_EXCEPTION`.

### 2. `calculate_mileage_reimbursement(distance_miles: float, requested_amount: float) -> dict`
Automates transportation policy checks by evaluating mileage claims against standard federal rates.
* **Current Rate**: $0.67 per mile.
* **Input Parameters**:
  * `distance_miles`: Claimed distance traveled in miles.
  * `requested_amount`: Amount requested by the employee.
* **Returns**:
  ```json
  {
    "computed_reimbursement": 67.00,
    "discrepancy": 8.00,
    "status": "FLAGGED_POLICY_EXCEPTION",
    "warning": "Requested amount exceeds federal rate of $0.67/mile by $8.00"
  }
  ```

### 3. `verify_required_documents(report_id: str) -> dict`
Checks whether required supporting invoices or documents have been uploaded to GCS for restricted categories (such as lodging and airline bookings).
* **Behavior**: Scans Firestore claims linked to the active report draft. If a lodging claim exists, it verifies that `has_receipt_attachment` is `true`.
* **Output**:
  ```json
  {
    "report_id": "rep_90182",
    "is_compliant": false,
    "missing_documents": ["lodging_invoice_receipt_gcs_hash"],
    "action_required": "Block report submission until receipt is uploaded"
  }
  ```

---

## 3. ADK Manifest Configurations

Our agent skills are wired using the Google Agent Development Kit (`acli` v0.5.0) framework. The metadata file `agents-cli-manifest.yaml` defines the agent lifecycle and hooks:

```yaml
name: ambient-expense-agent
acli_version: 0.5.0
agent_directory: app
region: us-east1
base_template: adk
generated_at: '2026-06-19T19:39:03.556174+00:00'
language: python
create_params:
  deployment_target: agent_runtime
  cicd_runner: skip
  include_data_ingestion: false
  datastore: none
  agent_guidance_filename: GEMINI.md
```

### Developer Knowledge Discovery
Using our built-in `google-developer-knowledge` lazy-loaded MCP server, developers and the agent runtime can query documentation live:
```bash
# Example query to find active travel guidelines
search_documents(query="domestic per diem allowance meals")
```

This prevents compliance rules from falling out of sync across different environments, giving the agent a single, immutable source of truth.
