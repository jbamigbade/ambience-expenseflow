# 🤖 Multi-Agent Design & Human-in-the-Loop Orchestration
**Track**: Agents for Business

This document explains the asynchronous, event-driven multi-agent system architecture of **Ambience ExpenseFlow**, illustrating how multiple logical agents coordinate state transitions through **Google Cloud Pub/Sub** and **Firebase Firestore** while maintaining a strict human-in-the-loop review boundary.

---

## 1. Multi-Agent Coordination Philosophy

Rather than a single, monolithic AI agent running in a blocking loop, Ambience ExpenseFlow uses a **decoupled asynchronous multi-agent coordination** pattern. Each participant in the ecosystem acts as an independent agent (some automated, some human):

1. **The Employee Ingestion Agent (Dashboard Frontend)**: Orchestrates client-side batch uploads to Google Cloud Storage (GCS) and translates user inputs into structured draft reports in Firebase Firestore.
2. **The Compliance Auditor Agent (Vertex AI Agent Runtime)**: An automated reasoning engine powered by Gemini 1.5 Pro via the Google Agent Development Kit (ADK). It analyzes receipt documents, extracts billing fields, and runs policy verification engines against active corporate rule structures.
3. **The Manager Approval Agent (Human Reviewer)**: Reviews pending claims, evaluates policy exceptions, and inputs mandatory justification notes to override flagged violations.
4. **The Event Broker (Google Cloud Pub/Sub)**: Links the independent modules asynchronously, delivering real-time status updates and keeping database states synchronized.

---

## 2. Asynchronous Event-Driven Architecture

The core of the multi-agent coordination is event-driven. By avoiding direct blocking HTTP calls between the dashboard and the AI agent, the platform remains fast, responsive, and resilient to transient network delays or prolonged LLM processing.

### Detailed State Coordination Flow
1. **Dossier Compiling**: The employee drafts an expense report. This creates a parent document in the Firestore `reports` collection.
2. **Batch Upload Event**: The employee uploads receipts. Files are streamed directly to GCS. Once complete, the dashboard publishes a message containing the GCS file reference to the `expense-reports` Pub/Sub topic.
3. **Asynchronous Analysis**: The Vertex AI Agent Runtime, listening on the Pub/Sub topic, is triggered asynchronously. The Gemini 1.5 Pro reasoning model downloads the receipt from GCS, extracts the merchant, date, category, and amount, and writes them as child documents in the Firestore `claims` collection, linked to the parent report.
4. **Compliance Checking**: The compliance engine parses each claims collection document. If a line item breaches defined limits (e.g., meal expense > $100, or a mileage claim rate deviating from $0.67/mile), the engine updates the claim state to `FLAGGED_POLICY_EXCEPTION`.
5. **Dashboard Push**: A Pub/Sub message pushes the completed claim extraction and status update back to the dashboard, refreshing the employee's screen without a page reload.

---

## 3. Human-in-the-Loop Compliance Override Flow

A major vulnerability of standard AI agents in enterprise settings is "unsupervised action"—allowing models to auto-approve expenses or reject claims based on parsing errors. 

Ambience ExpenseFlow implements a strict **Human-in-the-Loop (HITL) Validation Fence**. An AI agent can flag or recommend, but *only an authenticated human manager can authorize a policy override*.

```
                         [ Claim Flagged as Exception ]
                                       |
                                       v
                     +-----------------------------------+
                     |   Manager Reviews Flagged Claim   |
                     +-----------------------------------+
                                       |
                                       | Decides to Approve Override
                                       v
                     +-----------------------------------+
                     |   Dashboard Enforces Modal Popup  |
                     +-----------------------------------+
                                       |
                                       | User inputs mandatory 'Justification'
                                       v
                     +-----------------------------------+
                     |   FastAPI Gates API /api/override |
                     +-----------------------------------+
                                       |
                                       | Verifies OAuth Session & Role (RBAC)
                                       v
                     +-----------------------------------+
                     |   Writes Immutable Audit Timeline |
                     |   - Logs actor_email, timestamp   |
                     |   - Logs justification, old/new   |
                     +-----------------------------------+
                                       |
                                       v
                         [ Document State -> APPROVED ]
```

### Key Technical Safeguards:
1. **OAuth Verification**: The dashboard gates the `/api/pending` and `/api/override` routes. When a manager initiates an override, the system extracts the manager's authenticated session email.
2. **Mandatory Justification**: The frontend enforces a block; the manager cannot hit the API without completing the justification field (`justification_note`). The API itself rejects empty justification payloads with an `HTTP 400 Bad Request`.
3. **Immutable Ledger Writing**: The FastAPI router initiates a Firestore transaction that:
   * Sets the claim status to `APPROVED`.
   * Appends an entry into the report's `audit_timeline` subcollection.
   * Logs: `actor_email` (e.g., `obamigbade@gmail.com`), `action` ("MANAGER_OVERRIDE"), `timestamp` (ISO format UTC), and `justification` (the string typed by the manager).

---

## 4. Multi-Agent Orchestration Sequence (Mermaid)

The sequence diagram below visualizes the end-to-end multi-agent orchestration:

```mermaid
sequence_sheet
sequenceDiagram
    autonumber
    actor Employee as Employee (User)
    participant EP as Employee Portal (FastAPI)
    participant GCS as GCS Bucket
    participant PS as Pub/Sub Topic (expense-reports)
    participant AI as Vertex AI Agent Runtime (ADK)
    participant DB as Firestore Database
    actor Manager as Manager (User)
    participant MD as Manager Dashboard (FastAPI)

    Employee->>EP: Drafts Multi-Line Report
    EP->>DB: Create report doc (State: DRAFT)
    Employee->>EP: Batch Uploads Receipts
    EP->>GCS: Stream files to secure GCS folder
    EP->>PS: Publish event "RECEIPT_UPLOADED" (GCS reference)
    PS-->>AI: Asynchronous push trigger
    Note over AI: Gemini 1.5 Pro parses receipt document
    AI->>DB: Write extracted claims (State: PENDING)
    Note over AI: Run policy engines (e.g., check per diem limits)
    AI->>DB: Flag claim (State: FLAGGED_POLICY_EXCEPTION)
    PS-->>EP: Refresh status on Employee screen
    
    Manager->>MD: Logs in & Filters Pending Approvals
    MD->>DB: Query pending/flagged claims
    DB-->>MD: Return claims
    MD->>Manager: Display flagged claim alert ($0.67/mile)
    Manager->>MD: Clicks 'Review' & Inputs Justification Note
    MD->>DB: Execute Transaction: Set Claim APPROVED + Append Audit Timeline
    Note over DB: Audit Timeline stores manager_email & justification permanently
    MD-->>Manager: State updated to APPROVED
```
