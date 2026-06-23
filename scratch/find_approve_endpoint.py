import re

main_path = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"
with open(main_path, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()

for idx, line in enumerate(lines):
    if "approve_report" in line or "/approve" in line:
        print(f"Line {idx+1}: {line}")
