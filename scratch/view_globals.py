with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
for var in ["EXPENSES_COL", "DOCUMENTS_COL", "DECISIONS_COL", "AUDIT_LOGS_COL", "COMPANIES_COL", "EMPLOYEES_COL"]:
    m = re.search(f'{var}\\s*=\\s*["\']([a-zA-Z0-9_]+)["\']', content)
    if m:
        print(f"{var} = {m.group(0)}")
