import sys

with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

content = "".join(lines[3200:3350])
sys.stdout.buffer.write(content.encode("utf-8"))
