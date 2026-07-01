# 🌟 Ambience ExpenseFlow — Kaggle Capstone Submission
### Track: Agents for Business | Subtitle: Enterprise AI-Powered Travel & Expense Management System

Ambience ExpenseFlow is a security-first, AI-assisted enterprise travel and expense compliance platform that automates corporate expense processing, enforces custom policy restrictions, and integrates human-in-the-loop review. Built with a pythonic FastAPI dashboard deployed to **Google Cloud Run**, data stored in **Firebase Firestore**, receipts uploaded to **Google Cloud Storage (GCS)**, and an event-driven system on **Google Cloud Pub/Sub**, the architecture incorporates a Gemini-powered **Vertex AI Agent Runtime** to intelligently parse receipts and evaluate claims.

---

## 🗺️ Submission Document Index

This Capstone package consists of the following documentation folders, each aligned with the Kaggle judging rubric:

1. **[PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md)**: Deep-dive into the business problem, target persona matrices, core corporate value, security framework, and hosting topology.
2. **[MULTI_AGENT_DESIGN.md](./MULTI_AGENT_DESIGN.md)**: Detailed examination of the multi-agent system, asynchronous coordination, and the human-in-the-loop decision boundaries.
3. **[MCP_INTEGRATION.md](./MCP_INTEGRATION.md)**: Specifications on Model Context Protocol (MCP) server integration, tool declarations, and agent skills mapping.
4. **[EVALUATION_SHOWCASE.md](./EVALUATION_SHOWCASE.md)**: Breakdown of our rigorous 38-test suite, synthetic evaluation datasets, prompt regression metrics, and immutable audit trailing.

---

## 🚀 Live Demo & Hosting Assets

* **Live Dashboard URL**: [https://expense-manager-dashboard-654812449031.us-west1.run.app](https://expense-manager-dashboard-654812449031.us-west1.run.app)
* **Active Production Revision**: `expense-manager-dashboard-00032-vj4`
* **Google Cloud Project ID**: `project-5d38f91a-29a3-45bd-8d4`
* **GCP Hosting Region**: `us-west1` (Dashboard) & `us-east1` (Agent Runtime)
* **Agent Framework**: Google Agent Development Kit (ADK) `v0.5.0`

---

## 🛠️ Quick Start & Local Execution

To run and verify the local test suite and dashboard:

### 1. Prerequisites
Ensure you have the `uv` package manager installed:
```bash
# Verify or install uv
pip install uv
```

### 2. Install Dependencies
```bash
# Navigate to project folder and install dependencies
cd Capstone
uv pip install -e .
```

### 3. Run Unit and Integration Tests
```bash
# Execute our comprehensive 38-test suite
uv run pytest tests/
```

### 4. Launch Local Development Server
```bash
# Start FastAPI dashboard locally
uv run uvicorn submission_frontend.main:app --reload --port 8000
```

---

## 📹 1. 5-Minute YouTube Demo Script
*Note: This script is structured to show off the visual aesthetics and technical backend depth of Ambience ExpenseFlow.*

* **[0:00 - 0:45] Intro & The Enterprise Pain Point**
  * *Visual*: High-resolution screens of the glassmorphic login screen (`/login`) showing the title "Ambience ExpenseFlow" and the subtitle "Enterprise AI-Powered Travel & Expense Management System" in dark-mode style.
  * *Audio (Voiceover)*: "Welcome to a demonstration of Ambience ExpenseFlow—the first security-first, AI-assisted expense management platform built entirely on Google Cloud Vertex AI and the Agent Development Kit. Today, corporate expense processing is broken. Employees waste hours typing receipt details, while managers struggle to audit complex regional policies, leading to massive financial leakage and administrative fatigue. Let's see how Ambience ExpenseFlow changes this forever."
* **[0:45 - 2:00] Employee Portal & Multi-File Processing**
  * *Visual*: Switching to the Employee view (`#reports-grid`). Demonstrating drag-and-drop receipt batch uploading. Showing the loading transitions as files upload to Google Cloud Storage.
  * *Audio (Voiceover)*: "Logged in securely via Google OAuth 2.0, our Employee Portal lets travelers compile claims across multiple travel weeks. When an employee uploads a receipt, the file is streamed to a private GCS bucket. Behind the scenes, a Pub/Sub message triggers the Vertex AI Agent Runtime. Running Gemini 1.5 Pro, the agent extracts structured details, associates them with the active report draft, and evaluates corporate per diem budgets in real-time."
* **[2:00 - 3:30] Manager Queue & Policy Guards**
  * *Visual*: Hovering over visual policy alerts on the Manager Approval Dashboard. Clicking "Review". Showing the popup requiring input for "Justification Note" to approve a flagged mileage exception ($0.67/mile).
  * *Audio (Voiceover)*: "Now we're in the Manager Approval Dashboard. Here, exceptions are flagged instantly. Instead of rejecting entire multi-line reports, managers can approve or reject individual line items. For policy-breaching claims, the system enforces a strict human-in-the-loop override boundary: managers must provide a detailed justification. This justification is permanently bound with the authenticated user email and recorded as an immutable ledger transaction in Firestore."
* **[3:30 - 4:15] Architecture & Scalability Under the Hood**
  * *Visual*: Displaying the Mermaid technical topology. Highlighting the decoupled, asynchronous Pub/Sub broker and Firestore persistence layers.
  * *Audio (Voiceover)*: "Under the hood, Ambience ExpenseFlow is built to scale for organizations with over 15,000 employees. We decouple heavy processing using Cloud Pub/Sub, while Firestore Native manages transactional states. Highly optimized indexes prevent bottleneck delays during peak submission cycles. Since everything is deployed as a serverless container on Google Cloud Run, it scales dynamically, keeping infrastructure costs to a minimum."
* **[4:15 - 5:00] Outro & Open Source Code Base**
  * *Visual*: Displaying the Passing Pytest run in the console (38/38 passed). Displaying the GitHub README.
  * *Audio (Voiceover)*: "With 38 comprehensive unit and integration tests validating our rules, the platform is robust, deployable, and secure. Ambience ExpenseFlow bridges the gap between raw LLM capabilities and strict enterprise compliance. Thank you for watching!"

---

## 📸 2. Media Gallery Checklist
Before submitting, ensure the following visual assets are captured and added to the Kaggle Media Gallery:

- [ ] **Asset 1: Secure Login Screen**
  * *Description*: Dark-mode glassmorphic page showing `/login` containing the title "Ambience ExpenseFlow - Enterprise AI-Powered Travel & Expense Management System" and the Google OAuth Single-Sign-On option.
- [ ] **Asset 2: Employee Workspace**
  * *Description*: View showing `#reports-grid` with draft states, total compiled balances, and the receipt upload drawer.
- [ ] **Asset 3: Manager Queue Overview**
  * *Description*: Highlighting active pendings (`/api/pending`) with colored status labels (Approved, Auto-Approved, Pending, Flagged Policy Exception).
- [ ] **Asset 4: Interactive Override Dialog**
  * *Description*: Capturing the manager popup box showing policy limit details ($0.67/mile rate warning) and the mandatory justification text input.
- [ ] **Asset 5: Compliance Audit Timeline**
  * *Description*: Detailed visual timeline displaying timestamps, action events (Drafted, Submitted, Overridden), and actor emails (`actor_email` logs).
- [ ] **Asset 6: Pytest Coverage Run**
  * *Description*: Terminal snippet verifying `38 passed` test suites inside the local virtual environment.
- [ ] **Asset 7: Architecture Sequence Diagram**
  * *Description*: SVG render of the system's Pub/Sub and GCS flow.

---

## 🖼️ 3. Cover Image Recommendation

For the Kaggle Capstone submission cover image, we recommend utilizing a sleek, premium-tech themed banner that conveys AI capability and corporate financial structure:

* **Composition**: 
  * A central, high-resolution mockup of a modern laptop screen displaying the **Ambience ExpenseFlow Manager Approval Dashboard** in dark mode (vibrant violet and deep teal glassmorphism).
  * Hovering above or emerging from the screen is a glowing, translucent network graph of nodes (representing Model Context Protocol tool connections and Pub/Sub events) leading into a stylized, shining brain icon (representing the Gemini 1.5 Pro reasoning agent).
  * Sleek physical receipt slips drifting into the laptop screen, being parsed into glowing lines of green code and neat dollar amounts ($128.50, $0.67/mile).
* **Color Palette**: Deep slate black (#0F172A), tech-indigo (#6366F1), and neon-mint green (#10B981) for high-contrast, premium aesthetic appeal.
* **Text Overlay**: 
  * Header: `Ambience ExpenseFlow` (Bold Sans-Serif font, Outfit or Inter)
  * Subtitle: `Enterprise AI-Powered Travel & Expense Management System` (Smaller, thin, white-indigo tracking)
  * Badges: `Vertex AI` | `Cloud Run` | `FastAPI` | `Firestore`

---

## 📋 4. Final Kaggle Submission Checklist

- [ ] **Documentation Completeness**
  * [x] `README.md` populated.
  * [x] `PROJECT_OVERVIEW.md` populated.
  * [x] `MULTI_AGENT_DESIGN.md` populated.
  * [x] `MCP_INTEGRATION.md` populated.
  * [x] `EVALUATION_SHOWCASE.md` populated.
- [ ] **Rubric Verification**
  * [x] Verified project aligns with **Agents for Business** track rules.
  * [x] Proven human-in-the-loop safety fences (override justifications).
  * [x] Mentioned specific ADK version (`v0.5.0`) and manifest details.
  * [x] Included actual Cloud Run revision hashes for deployability checks.
- [ ] **Visual Assets & Media**
  * [ ] Record 5-minute video presentation following the YouTube script.
  * [ ] Capture the 7 checklist images from the dashboard browser.
- [ ] **Live Deployments & Endpoints**
  * [x] Verify live URL is running and returned 200 on smoke tests.
  * [x] Ensure Firebase collections are populated with legacy and fresh records.

---

## 🙏 Soli Deo Gloria — Acknowledgement

> All glory and thanksgiving to God the Father, God the Son, and God the Holy Spirit for the wisdom, grace, and opportunity to build solutions that serve people and glorify Him.

---
*Created and verified by John Bamigbade, Capstone Candidate.*
