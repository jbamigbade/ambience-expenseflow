import sys

with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "def run_per_diem_check" in line:
        content = "".join(lines[idx:idx+80])
        sys.stdout.buffer.write(content.encode("utf-8"))
        break
