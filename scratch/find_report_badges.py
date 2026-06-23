import re

main_path = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"
with open(main_path, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()

print("Searching for status badge helpers...")
for idx, line in enumerate(lines):
    if "function" in line and ("Badge" in line or "badge" in line):
        print(f"Line {idx+1}: {line}")
    elif '"draft"' in line or "'draft'" in line:
        if "badge" in line or "Badge" in line or "style" in line:
            print(f"Line {idx+1}: {line}")
