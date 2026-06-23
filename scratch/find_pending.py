import re

main_path = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"
with open(main_path, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()

print("Searching for approveReportForReview...")
for idx, line in enumerate(lines):
    if "approveReportForReview" in line:
        print(f"Line {idx+1}: {line}")

print("Searching for approved_with_exceptions...")
for idx, line in enumerate(lines):
    if "approved_with_exceptions" in line:
        print(f"Line {idx+1}: {line}")

print("Searching for pending approvals HTML...")
for idx, line in enumerate(lines):
    if 'id="pending"' in line or 'id="pending-tab"' in line or 'Pending Approvals' in line:
        if idx < 8000: # only show some early ones or later ones if relevant
            continue
        print(f"Line {idx+1}: {line}")
