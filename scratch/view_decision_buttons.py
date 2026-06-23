import sys

with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = list(re.finditer(r'(?:approve-btn|btn-approve|btn-reject|approve_claim)', content, re.IGNORECASE))
for m in matches:
    start = max(0, m.start() - 100)
    end = min(len(content), m.end() + 600)
    sys.stdout.buffer.write(f"--- MATCH ---\n".encode("utf-8"))
    sys.stdout.buffer.write(content[start:end].encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
