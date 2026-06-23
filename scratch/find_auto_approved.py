with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = re.finditer(r'auto_approved', content)
for m in matches:
    start = max(0, m.start() - 100)
    end = min(len(content), m.end() + 100)
    print("MATCH:\n", content[start:end], "\n")
