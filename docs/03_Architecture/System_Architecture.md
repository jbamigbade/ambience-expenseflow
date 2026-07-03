# Ambience ExpenseFlow
# System Architecture

## Document Information

| Field                       | Value                       |
|-----------------------------|---------------------------|
| Document ID                 | AEF-ARCH-001                |
| Document Title              | System Architecture         |
| Product                     | Ambience ExpenseFlow        |
| Version                     | 1.0                         |
| Status                      | Draft                       |
| Classification              | Confidential – Internal     |
| Owner                       | Engineering                 |
| Author                      | John Bamigbade              |
| Created                     | July 2026                   |
| Review Frequency            | Quarterly                   |
| Related Documents | PRD, SRS, Functional Requirements, Database Design, API Architecture |

---

## 1. Executive Summary

Ambience ExpenseFlow is an AI-powered enterprise Travel & Expense Management platform designed to manage the full expense lifecycle, including expense creation, multi-line reports, approvals, audit trail, finance review, corporate card reconciliation, reporting, and AI-assisted compliance.

The architecture is designed to be modular, cloud-native, secure, scalable, auditable, and extensible.

---

## 2. Architecture Goals

The system architecture must support:

- Multi-user role-based access
- Multi-line expense reports
- Manager approvals
- Finance review
- Audit trail
- Query builder
- CSV/Excel exports
- AI compliance review
- Corporate card readiness
- Future ERP integrations
- Future multi-tenant SaaS deployment

---

## 3. High-Level Architecture

```text
User Browser
    ↓
FastAPI Web Application
    ↓
Authentication Layer
    ↓
Route Layer
    ↓
Service Layer
    ↓
Business Logic / Workflow Engine
    ↓
Data Layer
    ↓
Firestore / Cloud Storage

AI-related workflow:

Expense Data / Receipt Data
    ↓
AI Compliance Engine
    ↓
Policy Review
    ↓
Risk Score / Recommendation
    ↓
Manager / Finance Decision
    ↓
Audit Trail

4. Major System Components
4.1 Frontend Layer

Responsible for:

Login page
Dashboard
My Reports
Submit Expense
Pending Approvals
Expense History
Audit Timeline
Marketing website

Current implementation:

HTML templates
CSS
JavaScript
FastAPI templates
Static assets
4.2 Backend Layer

Responsible for:

API routes
Authentication
Expense workflows
Approval workflows
Audit events
Data validation
Export generation
AI service orchestration

Current implementation:

FastAPI
Modular route structure
Services
Utilities
Schemas
Middleware
4.3 Authentication Layer

Supports:

Local development/test mode
Google OIDC
Future Microsoft Entra ID
Future SSO
Role-based access control

Roles:

Employee
Manager
Finance Admin
Auditor
Administrator
4.4 Expense Workflow Engine

Responsible for:

Expense report creation
Multi-line item support
Draft management
Report submission
Manager queue
Finance review
Status transitions
Reimbursement readiness
4.5 Audit Engine

Responsible for recording:

Who changed data
What changed
Previous value
New value
Timestamp
Action type
Reviewer decision
Export activity

Audit records must be immutable.

4.6 AI Engine

Responsible for:

Compliance checking
Policy warnings
Missing information detection
Duplicate detection roadmap
Receipt OCR roadmap
Fraud scoring roadmap
Natural language query roadmap
4.7 Data Layer

Primary storage:

Firestore

Supporting storage:

Cloud Storage for receipts/documents
Future data warehouse for analytics

5. Current Modular Structure

submission_frontend/
│
├── main.py
├── config/
├── middleware/
├── models/
├── routes/
├── schemas/
├── services/
├── static/
├── templates/
└── utilities/

6. Deployment Architecture

Current environment:

Local FastAPI development server
Google Cloud services
Firestore
Vertex AI
Cloud Storage

Target production:

Cloud Load Balancer
    ↓
Cloud Run / Containerized FastAPI App
    ↓
Firestore
    ↓
Cloud Storage
    ↓
Vertex AI
    ↓
Monitoring / Logging

7. Security Architecture Overview

Security design includes:

Authentication
Session management
Role-based access control
Audit logging
Data encryption
Secure secrets management
Least privilege access
Future MFA and SSO

8. Integration Architecture

Planned integrations include:

Google Workspace
Microsoft Entra ID
QuickBooks
Xero
NetSuite
SAP
Oracle
Ramp
Brex
Plaid
Stripe
American Express
Visa
Mastercard

9. Scalability Considerations

The architecture should support:

Growing user base
Multi-company support
Large report volumes
Export workloads
AI processing queues
Background sync jobs
Future multi-region deployment

10. Reliability Considerations

System reliability requires:

Automated tests
Health endpoints
Logging
Error monitoring
Backup strategy
Disaster recovery planning
Non-blocking AI calls
Graceful failure handling

11. Architecture Principles

Ambience ExpenseFlow architecture follows these principles:

Modular design
Separation of concerns
Secure by default
Auditable by design
Cloud-native
API-ready
AI-assisted, not AI-dependent
Backward compatible
Testable
Scalable

12. Future Architecture Enhancements

Planned enhancements:

Multi-tenant organization model
Dedicated admin console
Background job queue
Export service
Notification service
Corporate card transaction service
ERP integration service
Data warehouse
Public API gateway
Mobile API layer

13. Conclusion

The Ambience ExpenseFlow system architecture provides a strong foundation for an enterprise-grade Travel & Expense Management SaaS platform. The design supports current capabilities while allowing future expansion into corporate cards, ERP integrations, AI automation, analytics, and enterprise security.