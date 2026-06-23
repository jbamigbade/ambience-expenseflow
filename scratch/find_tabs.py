with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = re.finditer(r'Pending Approvals', content, re.IGNORECASE)
for m in matches:
    start = max(0, m.start() - 200)
    end = min(len(content), m.end() + 200)
    print("MATCH:\n", content[start:end], "\n")
