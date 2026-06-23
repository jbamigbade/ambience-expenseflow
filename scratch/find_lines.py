# Find occurrences of patterns in submission_frontend/main.py with line numbers
import re

patterns = [
    r'def enrich_claim_with_employee_info',
    r'useDemoClaimant',
    r'form-demo-select',
    r'get_pending',
    r'post_action',
    r'get_expenses',
    r'get_expense_detail',
    r'get_audit_trail',
    r'create_employee_claim',
    r'fetchExpenseHistory',
    r'loadAuditTrail',
    r'fetchPendingApprovals',
    r'add_audit_log'
]

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        for pattern in patterns:
            if re.search(pattern, line):
                print(f"Match for '{pattern}' on Line {idx}: {line.strip()}")
