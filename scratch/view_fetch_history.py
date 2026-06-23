import sys

with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = list(re.finditer(r'async function fetchExpenseHistory', content))
for m in matches:
    start = max(0, m.start() - 50)
    end = min(len(content), m.end() + 2500)
    sys.stdout.buffer.write(content[start:end].encode("utf-8"))
