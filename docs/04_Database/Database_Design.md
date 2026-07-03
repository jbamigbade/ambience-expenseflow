# Ambience ExpenseFlow
# Database Design

## Document Information

| Field | Value |
|--------|-------|
| Document ID | AEF-DB-001 |
| Document Title | Database Design |
| Product | Ambience ExpenseFlow |
| Subtitle | Enterprise Travel & Expense Management Platform |
| Version | 1.0 |
| Status | Draft |
| Classification | Confidential – Internal |
| Owner | Database Engineering |
| Author | John Bamigbade |
| Reviewer | Solution Architect |
| Created | July 2026 |
| Review Frequency | Quarterly |
| Related Documents | SRS, System Architecture, API Documentation |

---

# Table of Contents

1. Executive Summary

2. Database Objectives

3. Database Architecture

4. Firestore Overview

5. Entity Relationships

6. Collections

7. Documents

8. Naming Standards

9. Data Types

10. Primary Keys

11. Relationships

12. Index Strategy

13. Security Rules

14. Data Validation

15. Transactions

16. Audit Data

17. Reporting Data

18. Corporate Cards

19. AI Data

20. Performance

21. Backup

22. Disaster Recovery

23. Future Expansion

---

# Executive Summary

The Ambience ExpenseFlow database provides the persistent storage layer for the enterprise expense management platform.

The database supports:

- Organizations
- Employees
- Expense Reports
- Expense Line Items
- Approvals
- Audit Logs
- AI Recommendations
- Corporate Cards
- Reporting
- Administration

Firestore is selected as the primary operational database because it provides scalability, managed infrastructure, flexible document storage, and seamless integration with Google Cloud services.

---

# Database Objectives

The database must support:

- Enterprise scalability
- Secure data storage
- Fast queries
- High availability
- Multi-organization support
- Immutable audit history
- Future analytics
- AI processing
- Corporate card reconciliation
- Regulatory compliance

---

# Database Architecture

```
Application

↓

Service Layer

↓

Firestore

↓

Cloud Storage

↓

Reporting

↓

Analytics
```

---

# Database Principles

The database follows these principles:

- Cloud-native
- Document-oriented
- Scalable
- Secure
- Auditable
- Highly available
- Extensible
- Multi-tenant ready

---

# Firestore Collections

The primary collections include:

```
organizations

users

expense_reports

expense_line_items

approvals

audit_logs

departments

projects

cost_centers

policies

notifications

corporate_cards

card_transactions

reimbursements

ai_reviews

exports

settings
```

Each collection is described in detail in **Firestore_Collections.md**.

---

# Collection Relationships

```
Organization
      │
      ├────────Users
      │
      ├────────Departments
      │
      ├────────Projects
      │
      └────────Expense Reports
                     │
                     ├────Expense Line Items
                     │
                     ├────Approvals
                     │
                     ├────Audit Logs
                     │
                     ├────AI Reviews
                     │
                     └────Reimbursements
```

---

# Primary Entity

Expense Report

Contains:

- Report ID
- Employee
- Organization
- Business Purpose
- Status
- Total Amount
- Dates
- Manager
- Finance Reviewer

One report contains multiple expense line items.

---

# Expense Line Items

Each line item contains:

- Expense Date
- Category
- Merchant
- Amount
- Currency
- Tax
- Description
- Receipt
- AI Result
- Card Transaction

---

# Approval Entity

Stores:

- Reviewer
- Decision
- Comments
- Timestamp
- Workflow Step

---

# Audit Entity

Every significant action generates an immutable audit record.

Stores:

- Previous Value
- New Value
- User
- Timestamp
- Action
- Source
- Device

---

# Corporate Card Entity

Stores:

- Card Provider
- Card Number (Masked)
- Employee
- Organization
- Status
- Linked Transactions

---

# AI Review Entity

Stores:

- Compliance Score
- Risk Score
- Policy Warnings
- Recommendation
- Confidence
- Processing Timestamp

---

# Notification Entity

Stores:

- Recipient
- Type
- Message
- Read Status
- Delivery Timestamp

---

# Security

Sensitive information shall be protected using:

- Firestore Security Rules
- IAM
- Encryption at Rest
- HTTPS
- RBAC
- Audit Logging

---

# Performance

Database targets:

- Read latency <100 ms
- Write latency <200 ms
- Horizontal scaling
- Optimized indexes
- Efficient queries

---

# Backup Strategy

Daily Firestore exports

Cloud Storage backup

Retention policies

Recovery testing

---

# Future Expansion

Future database capabilities include:

- Multi-region replication
- BigQuery warehouse
- Data Lake
- Machine Learning datasets
- Historical analytics
- ERP synchronization
- Multi-tenant partitioning

---

# Conclusion

The Ambience ExpenseFlow database architecture provides a secure, scalable, cloud-native foundation for enterprise expense management while supporting AI capabilities, auditability, compliance, and future product growth.

---

# Document Control

## Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | July 2026 | John Bamigbade | Initial database architecture |

---

## Review & Approval

| Role | Name | Status |
|------|------|--------|
| Author | John Bamigbade | Approved |
| Database Architect | TBD | Pending |
| Solution Architect | TBD | Pending |

---

## Related Documents

- AEF-REQ-001 Software Requirements Specification
- AEF-ARCH-001 System Architecture
- AEF-ARCH-002 Cloud Architecture
- AEF-API-001 REST API
- AEF-DB-002 Firestore Collections
- AEF-DB-003 ER Diagram

---

© 2026 Ambience ExpenseFlow

Confidential – Internal Use Only.