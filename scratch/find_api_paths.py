with open('submission_frontend/static/js/dashboard.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re
api_paths = set(re.findall(r'\"/api/.*?\"|\'/api/.*?\'|`/api/.*?`', content))
for p in sorted(api_paths):
    print(p)
