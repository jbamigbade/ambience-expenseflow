with open('submission_frontend/static/js/dashboard.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re
# Regex to find fetch() calls
matches = re.finditer(r'fetch\((.*?)\)', content)
for m in matches:
    print(m.group(0))
