import re

main_path = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"
with open(main_path, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()

print("Searching for pending approvals section HTML...")
found = False
for idx, line in enumerate(lines):
    if 'id="pending"' in line or 'Pending Approvals' in line or 'id="pending-claims-list"' in line:
        print(f"Line {idx+1}: {line}")
        found = True

if not found:
    print("No pending/Pending Approvals exact matches in HTML. Trying lowercase 'pending'...")
    for idx, line in enumerate(lines):
        if 'pending' in line.lower() and ('tab' in line.lower() or 'filter' in line.lower() or 'class="' in line.lower()):
            if idx > 7000:
                print(f"Line {idx+1}: {line}")
