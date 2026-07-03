# Ambience ExpenseFlow
# Firestore Index Strategy

## Document Information

| Field                  | Value                                                       |
|------------------------|-------------------------------------------------------------|
| Document ID            | AEF-DB-004                                                  |
| Document Title         | Firestore Index Strategy                                    |
| Product                | Ambience ExpenseFlow                                        |
| Subtitle               | Enterprise Travel & Expense Management Platform             |
| Version                | 1.0                                                         |
| Status                 | Draft                                                       |
| Classification         | Confidential – Internal                                     |
| Owner                  | Database Engineering                                        |
| Author                 | John Bamigbade                                              |
| Reviewer               | Solution Architect                                          |
| Created                | July 2026                                                   |
| Last Updated           | July 2026                                                   |
| Review Frequency       | Quarterly                                                   |
| Related Documents      | Database Design, Firestore Collections, REST API              |

---

# Table of Contents

1. Executive Summary
2. Purpose
3. Firestore Index Fundamentals
4. Single-Field Indexes
5. Composite Indexes
6. Query Patterns
7. Performance Strategy
8. Reporting Queries
9. Dashboard Queries
10. Audit Queries
11. AI Queries
12. Corporate Card Queries
13. Future Optimization
14. Conclusion

---

# 1. Executive Summary

Firestore automatically indexes individual fields, but enterprise applications require carefully designed composite indexes to support complex filtering, sorting, and reporting.

This document defines the indexing strategy for Ambience ExpenseFlow to ensure high-performance queries as the platform scales.

---

# 2. Objectives

The indexing strategy must:

- Support fast dashboard loading
- Optimize search performance
- Reduce query latency
- Support reporting
- Support audit investigations
- Scale to millions of documents
- Minimize unnecessary indexes

---

# 3. Firestore Index Types

## Single-Field Indexes

Automatically created by Firestore.

Example:

- status
- employee_id
- organization_id
- created_at

---

## Composite Indexes

Required when combining:

- Multiple filters
- Filter + sort
- Multiple sort fields

---

# 4. Expense Report Indexes

## IDX-001

Collection

expense_reports

Fields

```
organization_id ASC
status ASC
submitted_at DESC
```

Supports

- Manager Dashboard
- Finance Dashboard
- Recent Submissions

---

## IDX-002

Collection

expense_reports

Fields

```
organization_id ASC
employee_id ASC
submitted_at DESC
```

Supports

"My Expense Reports"

---

## IDX-003

```
organization_id ASC
manager_id ASC
status ASC
```

Supports

Pending Approvals

---

## IDX-004

```
organization_id ASC
department_id ASC
submitted_at DESC
```

Supports

Department Reporting

---

## IDX-005

```
organization_id ASC
cost_center ASC
submitted_at DESC
```

Supports

Finance Reporting

---

# 5. Expense Line Item Indexes

## IDX-006

```
report_id ASC
expense_date DESC
```

Supports

Expense Details

---

## IDX-007

```
merchant ASC
expense_date DESC
```

Supports

Merchant Search

---

## IDX-008

```
category ASC
expense_date DESC
```

Supports

Category Reports

---

# 6. Audit Indexes

## IDX-009

```
report_id ASC
timestamp DESC
```

Supports

Audit Timeline

---

## IDX-010

```
user_id ASC
timestamp DESC
```

Supports

User Activity

---

## IDX-011

```
action ASC
timestamp DESC
```

Supports

Security Review

---

# 7. Approval Indexes

## IDX-012

```
reviewer_id ASC
status ASC
timestamp DESC
```

Supports

Manager Queue

---

## IDX-013

```
report_id ASC
timestamp DESC
```

Supports

Approval History

---

# 8. Reimbursement Indexes

## IDX-014

```
payment_status ASC
payment_date DESC
```

Supports

Finance Payments

---

# 9. Corporate Card Indexes

## IDX-015

```
employee_id ASC
transaction_date DESC
```

Supports

Employee Card Transactions

---

## IDX-016

```
provider ASC
status ASC
```

Supports

Card Administration

---

# 10. AI Review Indexes

## IDX-017

```
report_id ASC
processed_at DESC
```

Supports

AI History

---

## IDX-018

```
risk_score DESC
processed_at DESC
```

Supports

Fraud Review

---

# 11. Notification Indexes

## IDX-019

```
recipient_id ASC
read ASC
created_at DESC
```

Supports

Notification Center

---

# 12. Export Indexes

## IDX-020

```
user_id ASC
generated_at DESC
```

Supports

Export History

---

# 13. Dashboard Query Patterns

Employee Dashboard

```
organization_id
employee_id
status
submitted_at
```

---

Manager Dashboard

```
organization_id
manager_id
status
submitted_at
```

---

Finance Dashboard

```
organization_id
status
payment_status
submitted_at
```

---

Audit Dashboard

```
organization_id
action
timestamp
```

---

Executive Dashboard

```
organization_id
department_id
submitted_at
```

---

# 14. Query Optimization

Guidelines

- Always filter by organization_id first
- Limit result sets
- Use pagination
- Avoid full collection scans
- Use composite indexes for dashboard queries
- Archive historical data when appropriate

---

# 15. Future Indexes

Future enhancements may require indexes for:

- Multi-currency reporting
- Budget forecasting
- AI recommendations
- ERP synchronization
- Travel bookings
- Purchase orders
- Vendor analytics

---

# 16. Monitoring

Monitor:

- Slow queries
- Missing indexes
- Read operations
- Write operations
- Storage usage
- Index growth

---

# 17. Maintenance

Review indexes:

- Quarterly
- Before major releases
- After new features
- Following performance testing

Remove unused indexes to reduce storage and write costs.

---

# 18. Conclusion

A well-designed indexing strategy is essential for maintaining responsive dashboards, efficient reporting, and scalable operations. The indexes defined in this document provide the foundation for supporting enterprise workloads while minimizing latency and controlling operational costs.

---

# Document Control

## Revision History

| Version            | Date      | Author           | Description                          |
|--------------------|-----------|------------------|--------------------------------------|
| 1.0                | July 2026 | John Bamigbade   | Initial Firestore index strategy |

---

## Review & Approval

| Role               | Name             | Status   |
|--------------------|------------------|----------|
| Author             | John Bamigbade   | Approved |
| Database Architect | TBD              | Pending  |
| Solution Architect | TBD              | Pending  |

---

## Related Documents

- AEF-DB-001 Database Design
- AEF-DB-002 Firestore Collections
- AEF-DB-003 ER Diagram
- AEF-API-001 REST API
- AEF-REQ-001 Software Requirements Specification

---

© 2026 Ambience ExpenseFlow

Confidential – Internal Use Only.