with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = re.findall(r'status\s*=\s*["\'][a-zA-Z0-9_]+["\']', content)
for m in set(matches):
    print(m)
