filepath = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "loadPending" in line or "load_pending" in line:
        print(f"Line {idx+1}: {line.strip()}")
