import re

main_path = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"
with open(main_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

queries = [
    "def get_pending",
    "def filter_and_enrich_claims",
    "fetchPendingApprovals",
    "getStatusBadgeHTML",
    "approveReportForReview",
    "Old CLI sessions hidden",
    "New Expense Report",
    "View Report",
    "Draft",
    "approved_by_manager",
    "pending_manager_review",
    "returned_to_employee",
    "approved_with_exceptions",
    "Personal Vehicle Gas",
    "recalculate_report_totals",
    "add_report_audit_log",
    "approve_report",
]

print("Searching main.py for key terms...")
for idx, line in enumerate(lines, 1):
    for q in queries:
        if q in line:
            print(f"Line {idx}: {line.strip()[:100]} (matched '{q}')")
