with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
print("Searching for occurrences of api/me:")
matches = re.finditer(r'/api/me', content)
for m in matches:
    start = max(0, m.start() - 100)
    end = min(len(content), m.end() + 300)
    print(f"Context:\n{content[start:end]}\n---")
