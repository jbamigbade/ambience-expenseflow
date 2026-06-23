import re

main_path = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"
with open(main_path, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()

print("Searching for status badge HTML or helper functions...")
for idx, line in enumerate(lines):
    if "status" in line and ("badge" in line or "Badge" in line) and "function" in line:
        print(f"Line {idx+1}: {line}")
    elif "status === " in line or 'status == "' in line or 'status === "' in line:
        if "approved_by_manager" in line or "draft" in line:
            if idx > 6000 and idx < 8500:
                print(f"Line {idx+1}: {line}")
