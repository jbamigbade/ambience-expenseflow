import re

file_path = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"

queries = [
    r"def enrich_claim_with_employee_info",
    r"@app\.get\(\"/api/pending\"\)",
    r"@app\.get\(\"/api/expenses\"\)",
    r"@app\.post\(\"/api/employee/claims\"\)",
    r"@app\.post\(\"/api/action/",
    r"def add_audit_log",
    r"id=\"form-demo-select\"",
    r"function fetchPendingApprovals",
    r"function fetchExpenseHistory",
    r"function loadAuditTrail",
    r"function showClaimDetails",
    r"employees"
]

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for q in queries:
    pattern = re.compile(q, re.IGNORECASE)
    print(f"=== Matches for query: {q} ===")
    matches = 0
    for idx, line in enumerate(lines):
        if pattern.search(line):
            print(f"Line {idx+1}: {line.strip()}")
            matches += 1
            if matches >= 15:
                print("... truncated matches ...")
                break
    print()
