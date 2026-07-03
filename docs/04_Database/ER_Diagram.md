# Ambience ExpenseFlow
# Entity Relationship Diagram (ER Diagram)

## Document Information

| Field              | Value                                                       |
|--------------------|-------------------------------------------------------------|
| Document ID        | AEF-DB-003                                                  |
| Document Title     | Entity Relationship Diagram                                 |
| Product            | Ambience ExpenseFlow                                        |
| Subtitle           | Enterprise Travel & Expense Management Platform             |
| Version            | 1.0                                                         |
| Status             | Draft                                                       |
| Classification     | Confidential – Internal                                     |
| Owner              | Database Architecture                                       |
| Author             | John Bamigbade                                              |
| Reviewer           | Solution Architect                                          |
| Created            | July 2026                                                   |
| Review Frequency   | Quarterly                                                   |
| Related Documents  | Database Design, Firestore Collections, System Architecture, REST API |

---

# Table of Contents

1. Executive Summary

2. Purpose

3. ER Diagram Overview

4. Core Business Entities

5. Relationship Definitions

6. Cardinality Rules

7. Primary Entities

8. Supporting Entities

9. Reporting Relationships

10. Future Expansion

---

# Executive Summary

Although Firestore is a document-oriented NoSQL database, a logical Entity Relationship Diagram (ERD) is maintained to document how the major business entities relate to one another.

The ERD provides:

- Business understanding
- Database planning
- API design support
- Integration guidance
- Reporting design
- Future migration planning

---

# Purpose

The ERD documents the logical relationships among all major entities within Ambience ExpenseFlow.

It is intended for:

- Product Managers
- Software Engineers
- Database Engineers
- QA Engineers
- Solution Architects
- Business Analysts
- Auditors

---

# Enterprise Entity Relationship Diagram

```text
                        Organization
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
      Users              Departments         Cost Centers
        │                     │                     │
        └──────────────┬──────┴──────────────┐
                       ▼                     ▼
                   Expense Reports       Projects
                          │
      ┌───────────────────┼────────────────────────┐
      │                   │                        │
      ▼                   ▼                        ▼
Expense Line Items    Approvals              Reimbursements
      │                   │                        │
      ├────────────┐       │                        │
      ▼            ▼       ▼                        ▼
 Receipts      AI Reviews Audit Logs        Notifications
      │
      ▼
Corporate Card Transactions
      │
      ▼
Corporate Cards
```

---

# Primary Business Entities

## Organization

Represents a customer company using Ambience ExpenseFlow.

One Organization contains:

- Users
- Departments
- Projects
- Cost Centers
- Expense Reports
- Policies

Relationship

```
Organization

1

↓

Many Users
```

---

## User

Represents:

- Employee
- Manager
- Finance
- Auditor
- Administrator

Relationships

One User

↓

Many Expense Reports

One Manager

↓

Many Employees

One User

↓

Many Notifications

---

## Expense Report

The central business entity.

Contains

- Business Purpose
- Total Amount
- Status
- Employee
- Manager
- Organization

Relationships

```
Expense Report

1

↓

Many Expense Line Items

1

↓

Many Approval Records

1

↓

Many Audit Records

1

↓

One Reimbursement
```

---

## Expense Line Item

Represents a single business expense.

Examples

- Hotel

- Airfare

- Meals

- Parking

- Fuel

- Taxi

- Mileage

Relationships

```
Expense Report

1

↓

Many Expense Line Items
```

---

## Approval

Stores every approval decision.

Relationship

```
Expense Report

1

↓

Many Approval Records
```

---

## Audit Log

Stores immutable history.

Relationship

```
Expense Report

1

↓

Many Audit Records
```

---

## Reimbursement

Represents payment made to the employee.

Relationship

```
Expense Report

1

↓

Zero or One Reimbursement
```

---

## Corporate Card

Represents an issued business card.

Relationship

```
Employee

1

↓

Many Corporate Cards
```

---

## Card Transaction

Imported transaction.

Relationship

```
Corporate Card

1

↓

Many Transactions
```

---

## AI Review

Stores AI-generated recommendations.

Relationship

```
Expense Report

1

↓

Many AI Reviews
```

---

## Notification

Represents system notifications.

Relationship

```
User

1

↓

Many Notifications
```

---

## Policy

Stores organization expense rules.

Relationship

```
Organization

1

↓

Many Policies
```

---

## Department

Relationship

```
Department

1

↓

Many Users
```

---

## Cost Center

Relationship

```
Cost Center

1

↓

Many Expense Reports
```

---

## Project

Relationship

```
Project

1

↓

Many Expense Reports
```

---

# Cardinality Matrix

| Parent | Child | Relationship |
|---------|-------|--------------|
| Organization | Users | 1 : Many |
| Organization | Departments | 1 : Many |
| Organization | Projects | 1 : Many |
| Organization | Policies | 1 : Many |
| User | Expense Reports | 1 : Many |
| Expense Report | Expense Line Items | 1 : Many |
| Expense Report | Approvals | 1 : Many |
| Expense Report | Audit Logs | 1 : Many |
| Expense Report | AI Reviews | 1 : Many |
| Expense Report | Reimbursement | 1 : 0..1 |
| Corporate Card | Transactions | 1 : Many |
| User | Notifications | 1 : Many |

---

# Referential Integrity

Although Firestore is schema-flexible, the application enforces logical integrity:

- Every Expense Report belongs to one Organization.
- Every Expense Report belongs to one Employee.
- Every Expense Line Item belongs to one Expense Report.
- Every Approval belongs to one Expense Report.
- Every Audit Log belongs to one Expense Report.
- Every Notification belongs to one User.

---

# Future Entity Expansion

Future releases may introduce:

- Vendors
- Budgets
- Purchase Orders
- Travel Bookings
- Exchange Rates
- ERP Synchronization
- Workflow Templates
- AI Models
- Approval Delegations
- Expense Forecasts

---

# Reporting Relationships

Business Intelligence will aggregate:

Organization

↓

Departments

↓

Expense Reports

↓

Expense Categories

↓

Monthly Spending

↓

Executive Dashboards

---

# Design Principles

The logical model follows these principles:

- Normalize business entities
- Minimize data duplication
- Support scalable Firestore collections
- Optimize reporting
- Enable secure access
- Support future integrations

---

# Conclusion

The Entity Relationship Diagram provides the conceptual blueprint for Ambience ExpenseFlow. Although Firestore stores data in collections and documents rather than relational tables, maintaining a logical ERD ensures consistent data modeling, supports system evolution, and provides a common understanding across engineering, product, and business teams.

---

# Document Control

## Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | July 2026 | John Bamigbade | Initial logical ER Diagram |

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
- AEF-ARCH-001 System Architecture
- AEF-REQ-001 Software Requirements Specification

---

© 2026 Ambience ExpenseFlow

Confidential – Internal Use Only.