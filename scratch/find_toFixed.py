import os
import sys

# Ensure UTF-8 printing
sys.stdout.reconfigure(encoding='utf-8')

filepath = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if ".toFixed" in line:
        print(f"Line {idx+1}: {line.strip()}")
        # print some context
        start = max(0, idx - 5)
        end = min(len(lines), idx + 6)
        print("--- CONTEXT ---")
        for j in range(start, end):
            prefix = ">>>" if j == idx else "   "
            print(f"{prefix} {j+1}: {lines[j].rstrip()}")
        print("-" * 50)
