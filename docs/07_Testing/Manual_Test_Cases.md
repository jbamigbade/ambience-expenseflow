# Ambience ExpenseFlow
# Manual Test Cases

## Document Information

| Field                | Val    ue                                         |
|----------------------|--------------------------------------------------|
| Document ID           | AEF-QA-001                                       |
| Document Title        | Manual Test Cases                                |
| Product               | Ambience ExpenseFlow                             |
| Version               | 1.0                                              |
| Status                | Draft                                            |
| Status                | Draft                                            |
| Classification        | Confidential – Internal                          |
| Owner                 | Quality Assurance                                |
| Author                | John Bamigbade                                   |
| Created               | July 2026                                        |
| Review Frequency      | Quarterly                                        |
| Related Documents     | SRS, Functional Requirements, UI/UX Specifications, API Specifications |

---

## 1. Executive Summary

This document defines manual test cases for Ambience ExpenseFlow. The purpose is to verify that core workflows function correctly before release, including authentication, expense submission, approvals, audit trail, exports, corporate cards, dashboards, and administrative configuration.

---

## 2. Testing Objectives

Manual testing must confirm that:

- Users can log in and log out successfully.
- Employees can create multi-line expense reports.
- Receipts can be uploaded and associated with line items.
- Managers can approve, reject, and return reports.
- Finance users can process reimbursement workflows.
- Audit logs are created for key actions.
- CSV and Excel exports work correctly.
- Role-based access control is enforced.
- Dashboards display accurate data.
- Errors are handled clearly.

---

## 3. Test Case Format

Each test case should include:

- Test Case ID
- Title
- Preconditions
- Test Steps
- Expected Result
- Actual Result
- Status
- Notes

---

## 4. Authentication Test Cases

### TC-AUTH-001 — Login Page Loads

Preconditions:

- Application is running.
- User opens `/login`.

Steps:

1. Navigate to the login page.
2. Verify the Ambience ExpenseFlow branding displays.
3. Verify login option is visible.

Expected Result:

- Login page loads successfully.
- Branding and subtitle are visible.

Status:

Pending

---

### TC-AUTH-002 — Local Test Login

Preconditions:

- Local test mode is enabled.

Steps:

1. Navigate to `/login`.
2. Click **Enter Dashboard**.
3. Verify dashboard loads.

Expected Result:

- User is authenticated in local mode.
- Dashboard displays correct user email and role.

Status:

Pending

---

### TC-AUTH-003 — Logout

Steps:

1. Log in.
2. Click **Logout**.
3. Verify redirect to login page.
4. Try opening dashboard URL again.

Expected Result:

- Session is cleared.
- User is redirected to login.

Status:

Pending

---

## 5. Employee Expense Test Cases

### TC-EXP-001 — Create Draft Expense Report

Steps:

1. Log in as employee.
2. Open **Submit Expense**.
3. Enter report title and business purpose.
4. Save as draft.

Expected Result:

- Draft report is saved.
- Report appears in My Reports.

Status:

Pending

---

### TC-EXP-002 — Add Multiple Line Items

Steps:

1. Open a draft report.
2. Add Hotel expense.
3. Add Meals expense.
4. Add Parking expense.
5. Verify total amount.

Expected Result:

- Multiple line items are added.
- Total updates correctly.

Status:

Pending

---

### TC-EXP-003 — Submit Expense Report

Steps:

1. Create a valid report.
2. Add at least one line item.
3. Upload required receipt.
4. Click Submit.

Expected Result:

- Report status changes from Draft to Submitted.
- Manager receives the report.

Status:

Pending

---

## 6. Receipt Test Cases

### TC-RCT-001 — Upload Receipt

Steps:

1. Open a line item.
2. Upload PNG, JPEG, or PDF receipt.
3. Save.

Expected Result:

- Receipt uploads successfully.
- Receipt preview or link is available.

Status:

Pending

---

### TC-RCT-002 — Missing Receipt Validation

Steps:

1. Create expense above receipt threshold.
2. Do not upload receipt.
3. Attempt to submit.

Expected Result:

- Submission fails.
- Missing receipt message appears.

Status:

Pending

---

## 7. Manager Approval Test Cases

### TC-APR-001 — View Pending Approvals

Steps:

1. Log in as manager.
2. Open Pending Approvals.
3. Verify submitted employee reports display.

Expected Result:

- Pending reports assigned to manager are visible.

Status:

Pending

---

### TC-APR-002 — Approve Report

Steps:

1. Open a pending report.
2. Review line items and receipts.
3. Click Approve.

Expected Result:

- Report moves to Finance Review or Approved state.
- Audit record is created.

Status:

Pending

---

### TC-APR-003 — Reject Report

Steps:

1. Open pending report.
2. Click Reject.
3. Enter rejection reason.

Expected Result:

- Report status becomes Rejected.
- Employee is notified.
- Audit record includes rejection reason.

Status:

Pending

---

## 8. Finance Test Cases

### TC-FIN-001 — View Approved Reports

Steps:

1. Log in as finance admin.
2. Open Finance Dashboard.
3. Verify approved reports are visible.

Expected Result:

- Approved reports awaiting payment display.

Status:

Pending

---

### TC-FIN-002 — Mark Report as Paid

Steps:

1. Select approved report.
2. Process reimbursement.
3. Mark as paid.

Expected Result:

- Report status becomes Paid.
- Reimbursement record is created.
- Audit log is created.

Status:

Pending

---

## 9. Audit Test Cases

### TC-AUD-001 — View Audit Timeline

Steps:

1. Open expense history.
2. Select a report.
3. Click View Trail.

Expected Result:

- Audit timeline displays actions in chronological order.

Status:

Pending

---

### TC-AUD-002 — Export Audit Records

Steps:

1. Open Audit Center.
2. Filter audit records.
3. Export to CSV.

Expected Result:

- CSV file downloads successfully.
- Export event is audited.

Status:

Pending

---

## 10. Export Test Cases

### TC-EXP-CSV-001 — Export Expense History to CSV

Steps:

1. Open Expense History.
2. Apply filter.
3. Click Export CSV.

Expected Result:

- CSV file downloads.
- File contains filtered records.

Status:

Pending

---

### TC-EXP-XLS-001 — Export Expense History to Excel

Steps:

1. Open Expense History.
2. Click Export Excel.

Expected Result:

- Excel file downloads.
- Formatting is readable.

Status:

Pending

---

## 11. Corporate Card Test Cases

### TC-CARD-001 — View Corporate Card Dashboard

Steps:

1. Log in as finance admin.
2. Open Corporate Cards.
3. Verify card transaction widgets display.

Expected Result:

- Active cards, matched transactions, and exceptions display.

Status:

Pending

---

### TC-CARD-002 — Match Card Transaction

Steps:

1. Open unmatched transaction.
2. Select matching expense line item.
3. Confirm match.

Expected Result:

- Transaction status becomes Matched.
- Audit record is created.

Status:

Pending

---

## 12. Admin Test Cases

### TC-ADM-001 — Create User

Steps:

1. Log in as administrator.
2. Open Admin Portal.
3. Create new user.
4. Assign role.

Expected Result:

- User is created.
- Role is assigned correctly.

Status:

Pending

---

### TC-ADM-002 — Configure Expense Policy

Steps:

1. Open Expense Policies.
2. Set receipt threshold.
3. Save policy.
4. Submit test expense above threshold.

Expected Result:

- New policy is enforced.

Status:

Pending

---

## 13. Role-Based Access Test Cases

### TC-RBAC-001 — Employee Cannot Approve Own Report

Steps:

1. Log in as employee.
2. Submit report.
3. Attempt to approve own report.

Expected Result:

- Approval is denied.

Status:

Pending

---

### TC-RBAC-002 — Auditor Read-Only Access

Steps:

1. Log in as auditor.
2. Open expense report.
3. Attempt to edit report.

Expected Result:

- Editing is blocked.
- Auditor can only view/export permitted data.

Status:

Pending

---

## 14. Smoke Test Checklist

Before every release, verify:

- Login works.
- Dashboard loads.
- Expense submission works.
- Manager approval works.
- Finance review works.
- Audit trail works.
- Export works.
- Logout works.

---

## 15. Conclusion

Manual testing ensures that Ambience ExpenseFlow works correctly across core business workflows before release. These test cases provide a foundation for QA validation, user acceptance testing, regression testing, and future automated test coverage.

---

## Document Control

| Version   | Date        | Author          | Description                           |
|-----------|-------------|-----------------|---------------------------------------|
| 1.0       | July 2026   | John Bamigbade  | Initial manual test cases             |

© 2026 Ambience ExpenseFlow  
Confidential – Internal Use Only.