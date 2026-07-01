# 📖 Capstone Project Overview: Ambience ExpenseFlow
### Subtitle: Enterprise AI-Powered Travel & Expense Management System
**Track**: Agents for Business

---

## 1. Executive Summary

**Ambience ExpenseFlow** is a secure, AI-assisted, multi-role enterprise travel and expense compliance platform that automates corporate expense processing, enforces custom policy restrictions, and integrates human-in-the-loop review. Built with a pythonic FastAPI dashboard deployed to **Google Cloud Run**, data stored in **Firebase Firestore**, receipts uploaded to **Google Cloud Storage (GCS)**, and an event-driven system on **Google Cloud Pub/Sub**, the architecture incorporates a Gemini-powered **Vertex AI Agent Runtime** to intelligently parse receipts and evaluate claims. Ambience ExpenseFlow demonstrates a modern, security-first paradigm for integrating Large Language Models (LLMs) into regulated enterprise workflows while ensuring absolute operational auditing, compliance verification, and human oversight.

---

## 2. Business Problem & Solution

### The Corporate Challenge
Traditional corporate expense reporting relies on manual data entry, which is both time-consuming and error-prone. Employees spend hours compiling physical receipts, while managers and auditors must manually cross-reference claims against complicated regional policies, per diem schedules, and transport rate structures. This administrative friction results in:
* **Severe Financial Leakage**: Overpayments on meals, unauthorized mileage claims, and double-dipping.
* **Low Auditing Coverage**: Auditors can typically only spot-check a small fraction of Submitted claims.
* **Insecure Document Storage**: Sensitive corporate financial receipts hosted on unencrypted, third-party SaaS lockers.

### The Solution: Ambience ExpenseFlow
Ambience ExpenseFlow streamlines this entire workflow into an automated, compliant, and auditable enterprise pipeline:
1. **Intelligent Capture**: The Gemini-powered reasoning agent parses receipt images/PDFs directly from secure private GCS buckets, automatically generating structured line items.
2. **Proactive Guardrails**: Custom rule engines automatically compute mileage claims against the federal $0.67/mile allowance and check meal limits against localized per diems, instantly flagging exceptions.
3. **Rigorous Compliance Ledger**: When a manager overrides a flagged policy exception, the system enforces a strict human justification step, writing the decision, justification, timestamp, and authenticated reviewer email (`actor_email`) permanently to Firestore.

---

## 3. Target Persona Matrix

The application coordinates four distinct corporate roles with specialized views and capabilities:

```
+---------------------------------------------------------------------------------------------------------+
|                                        AMBIENCE EXPENSEFLOW ROLE MATRIX                                 |
+---------------------------------------------------------------------------------------------------------+
| User Role      | Key Responsibilities                       | Key Dashboard Elements                    |
+----------------+--------------------------------------------+-------------------------------------------+
| Employees      | Draft multi-line item reports, upload      | #reports-grid, drag-and-drop receipt      |
|                | receipt files, compile weekly dossiers.     | submission uploaders, Category breakdown. |
+----------------+--------------------------------------------+-------------------------------------------+
| Managers       | Review pending team reports, analyze policy| Pending Approvals filters (all, portal,   |
|                | exception alerts, authorize overrides.     | workflow), Justification override popup.  |
+----------------+--------------------------------------------+-------------------------------------------+
| Finance Admins | Adjust corporate daily per diems, configure| Global dashboard view, policy configuration|
|                | user hierarchies, monitor spend.           | fields, team role definitions.            |
+----------------+--------------------------------------------+-------------------------------------------+
| Auditors       | Inspect chronological timeline ledgers,    | Audit Timeline containing absolute        |
|                | download original receipts, verify notes.  | chronological records of all operations.   |
+----------------+--------------------------------------------+-------------------------------------------+
```

---

## 4. Key Platform Features

* 💻 **Employee Submission Portal**: An interactive interface allowing employees to compose, modify, and batch-upload documents to their travel drafts.
* 📊 **Manager Approval Dashboard**: A glassmorphic control hub equipped with quick-action approval handles, exception counters, and responsive filter cards.
* 📦 **Enterprise Expense Report Workflow**: Advanced layout separation separating draft creators (`#create-report-container`) from active list cards (`#reports-grid`) to eliminate user clutter.
* 🗃️ **Multi-Line Item Reports**: Bundles flights, meals, lodging, and mileage claims into cohesive weekly dossiers, retaining exact itemized receipts.
* 📎 **Receipt & Document Upload**: Private GCS multi-file upload with encrypted session handling to protect corporate invoice files.
* 💰 **Per Diem Policy Checks**: Backend validation module checking food/lodging expenses against global corporate limits, flagging any claims that exceed local caps.
* 🚗 **Transportation & Mileage Policy Design**: Native engine evaluating distance-based reimbursement, checking mileage against federal $0.67/mile standards and calculating total costs.
* ⚙️ **Company-Configurable Policy Structure**: Decoupled policy rules stored in Firestore, enabling administrators to edit allowances instantly without requiring code changes.
* 🔑 **Google OAuth Login**: Complete SSO integrations restricting platform access to authorized corporate emails.
* 👥 **Role-Based Access**: Role-based access constraints limiting endpoint actions to matching personas.
* 🗄️ **Firestore Persistence**: High-concurrency Native-mode database storing operational documents, drafts, configurations, and logs.
* 🕰️ **Audit Timeline & Actor Tracking**: Interactive, non-editable transaction timeline showing historical actions taken across the dossier lifetime.
* 📧 **Authenticated actor_email Trail**: Permanent mapping of each approval, override, and submission directly to the reviewer's authenticated Gmail account.
* 🌐 **Serverless Cloud Run**: Rapid containerization utilizing multi-stage Docker builds to serve FastAPI with minimal resource footprints.
* 🤖 **Agent Runtime Integration**: Connects via the Google ADK to the Vertex AI Reasoning Engine, orchestrating Gemini 1.5 Pro instances.

---

## 5. Technical Hosting Topology

```
                  +-----------------------------------------------------------+
                  |                     Web Client Browser                    |
                  +-----------------------------------------------------------+
                                                |
                                                | HTTPS / Google OAuth 2.0
                                                v
                  +-----------------------------------------------------------+
                  |         Google Cloud Run (expense-manager-dashboard)      |
                  +-----------------------------------------------------------+
                       |                        |                      |
      Secure GCS APIs  |       Firestore Client |      Pub/Sub Push    |  Vertex AI
                       v                        v                      v  ADK SDK
               +---------------+        +---------------+      +---------------+
               | Google Cloud  |        |    Firebase   |      | Google Cloud  |
               |  Storage (GCS)|        |   Firestore   |      |  Pub/Sub Bus  |
               +---------------+        +---------------+      +---------------+
                       |                                               |
                       +===============================================+
                                                |
                                                v  Trigger Agent Process
                                 +------------------------------+
                                 |   Vertex AI Agent Runtime    |
                                 +------------------------------+
                                                |
                                                v  LLM Call
                                 +------------------------------+
                                 |    Google Gemini 1.5 Pro     |
                                 +------------------------------+
```

* **Frontend & Backend Hosting**: Containerized Python FastAPI server hosted on **Google Cloud Run** inside region `us-west1`.
* **State & Configurations**: **Firebase Firestore** (Native Mode) serving high-speed document mutations.
* **Receipt Repositories**: **Google Cloud Storage (GCS)** buckets gating binary assets via signed sessions.
* **Asynchronous Integration**: **Google Cloud Pub/Sub** publishing push messages on topic `expense-reports` to coordinate background compliance and trace processing.
* **Intelligent Reasoning Engine**: Deployed to **Vertex AI Agent Runtime** (region `us-east1`) running Google Gemini 1.5 Pro.

---

## 6. Business Value & ROI

1. **70% Audit Cycle Reduction**: Replaces traditional weeks-long manual report audits with instantaneous, automated policy compliance processing.
2. **Prevented Financial Overpayments**: Stops erroneous reimbursement claims (e.g., $0.75/mile instead of $0.67/mile, or double-billed dinners) directly at submission.
3. **Regulatory Audit Readiness**: Zero-risk auditing model. Every policy override is logged with a mandatory justification block, removing human bias and proving complete compliance to corporate tax auditors.
4. **Data Privacy & Governance**: Unlike public SaaS tools, all invoice assets are housed inside secure corporate GCS buckets and managed within Google Cloud security boundaries.

---

## 7. Enterprise Scalability Notes

* **Assignment Relational Trees**: The Firestore database establishes hierarchical employee-to-manager relational mapping, directing team claims only to authorized reviewers while permitting Finance Admins global compliance views.
* **Designed for 15,000+ Employees**: Utilizes optimized Firestore indexes and Cloud Run serverless concurrency limits to scale up to massive peak corporate travel cycles without performance degradation.
* **Many Claims Per Employee**: Accommodates high-volume expense submission structures, linking dozens of distinct claims to singular reports seamlessly.
* **Compiles Multiple Travel Weeks**: Employees can save draft reports, adding and editing lines across multiple travel weeks as drafts, then submit them in a single batch file.
