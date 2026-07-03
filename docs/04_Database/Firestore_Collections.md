# Ambience ExpenseFlow
# Firestore Collections

## Document Information

| Field                         | Value                     |
|-------------------------------|---------------------------|
| Document ID                   | AEF-DB-002                |
| Document Title                | Firestore Collections     |
| Product                       | Ambience ExpenseFlow      |
| Version                       | 1.0                       |
| Status                        | Draft                     |
| Classification                | Confidential – Internal   |
| Owner                         | Database Engineering      |
| Author                        | John Bamigbade            |
| Created                       | July 2026                 |
| Status                        | Draft                     |
| Classification                | Confidential – Internal   |
| Owner                         | Database Engineering      |
| Author                        | John Bamigbade            |
| Created                       | July 2026                 |
| Review Frequency              | Quarterly                 |
| Related Documents | Database Design, REST API, SRS |

---

# Executive Summary

This document defines every Firestore collection used by Ambience ExpenseFlow.

Each collection includes:

- Purpose
- Document structure
- Field definitions
- Relationships
- Validation rules
- Security considerations
- Related APIs
- Related UI screens
- Sample document

---

# Database Overview

```
organizations
│
├── users
├── departments
├── cost_centers
├── projects
├── expense_reports
│      ├── expense_line_items
│      ├── approvals
│      ├── audit_logs
│      ├── ai_reviews
│      └── reimbursements
│
├── corporate_cards
├── card_transactions
├── notifications
├── exports
├── policies
└── settings
```

---

# Collection 1

# organizations

Purpose

Stores each customer organization.

Primary Key

organization_id

Example Fields

| Field | Type |
|---------|------|
| organization_id | String |
| organization_name | String |
| industry | String |
| subscription_plan | String |
| status | String |
| created_at | Timestamp |
| updated_at | Timestamp |

Relationships

One organization contains:

- Users
- Departments
- Projects
- Expense Reports
- Policies

---

# Collection 2

# users

Purpose

Stores employees and administrators.

Primary Key

user_id

Example Fields

| Field | Type |
|---------|------|
| user_id | String |
| organization_id | String |
| first_name | String |
| last_name | String |
| email | String |
| role | String |
| department_id | String |
| manager_id | String |
| active | Boolean |

Roles

- Employee
- Manager
- Finance
- Auditor
- Administrator

Related UI

Employee Portal

Manager Dashboard

Admin Portal

---

# Collection 3

# departments

Purpose

Stores organizational departments.

Fields

department_id

organization_id

name

cost_center

manager_id

status

---

# Collection 4

# cost_centers

Stores financial cost centers.

Example

Marketing

Sales

Finance

Operations

Research

IT

---

# Collection 5

# projects

Stores billable projects.

Fields

project_id

organization_id

project_name

client

budget

status

---

# Collection 6

# expense_reports

Purpose

Master expense report.

Fields

| Field | Type |
|---------|------|
| report_id | String |
| organization_id | String |
| employee_id | String |
| manager_id | String |
| title | String |
| business_purpose | String |
| status | String |
| total_amount | Decimal |
| currency | String |
| submitted_at | Timestamp |

Status

Draft

Submitted

Approved

Rejected

Returned

Finance Review

Paid

Related APIs

Create Report

Update Report

Submit Report

Approve Report

---

# Collection 7

# expense_line_items

Purpose

Stores every expense inside a report.

Relationship

Many

↓

One Expense Report

Fields

expense_item_id

report_id

expense_date

merchant

category

amount

tax

currency

description

receipt_url

ai_status

card_transaction_id

Example Categories

Airfare

Hotel

Meals

Mileage

Parking

Taxi

Fuel

Office Supplies

Entertainment

Training

Internet

Miscellaneous

---

# Collection 8

# approvals

Stores workflow approvals.

Fields

approval_id

report_id

reviewer_id

decision

comments

step

timestamp

Decision

Approved

Rejected

Returned

Escalated

Delegated

---

# Collection 9

# audit_logs

Purpose

Immutable history.

Fields

audit_id

report_id

user

action

old_value

new_value

timestamp

device

browser

ip_address

---

# Collection 10

# reimbursements

Stores payment information.

Fields

payment_id

report_id

employee

payment_date

payment_method

reference

status

---

# Collection 11

# corporate_cards

Fields

card_id

organization

provider

employee

masked_number

status

---

# Collection 12

# card_transactions

Stores imported transactions.

Fields

transaction_id

card_id

merchant

amount

currency

transaction_date

matched_report

status

---

# Collection 13

# ai_reviews

Stores AI recommendations.

Fields

review_id

report_id

risk_score

compliance_score

recommendation

confidence

warnings

processed_at

---

# Collection 14

# notifications

Fields

notification_id

recipient

title

message

type

read

created_at

---

# Collection 15

# exports

Stores export history.

Fields

export_id

user

format

generated_at

download_url

status

---

# Collection 16

# policies

Stores expense policies.

Examples

Receipt threshold

Mileage rate

Per diem

Maximum hotel

Approval limits

---

# Collection 17

# settings

Stores organization configuration.

Examples

Branding

Workflow

AI settings

Security settings

Notification settings

Currency

Tax

---

# Security Rules

Every collection follows:

- Organization isolation
- RBAC
- Audit logging
- Encryption
- Least privilege

---

# Naming Standards

Collection Names

lowercase_plural

Field Names

snake_case

IDs

UUID

Timestamps

UTC

---

# Future Collections

Future versions may introduce:

travel_bookings

budgets

vendors

purchase_orders

erp_sync

exchange_rates

attachments

workflow_templates

---

# Conclusion

The Firestore data model provides a scalable, secure, and extensible foundation for Ambience ExpenseFlow while supporting future enterprise features, AI services, analytics, and third-party integrations.

---

# Document Control

## Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | July 2026 | John Bamigbade | Initial Firestore collection design |

---

© 2026 Ambience ExpenseFlow

Confidential – Internal Use Only.