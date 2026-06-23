import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer("async function fetchExpenseHistory", content)]
for m in matches:
    print(content[m+1100:m+3000])
