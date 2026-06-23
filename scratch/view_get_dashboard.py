import sys

with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "def get_dashboard" in line:
        content = "".join(lines[idx:idx+150])
        sys.stdout.buffer.write(content.encode("utf-8"))
        break
