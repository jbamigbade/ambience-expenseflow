with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
print("Searching for USER_ROLE definition:")
matches = re.finditer(r'USER_ROLE', content)
for m in matches:
    start = max(0, m.start() - 100)
    end = min(len(content), m.end() + 150)
    print(f"Context:\n{content[start:end]}\n---")
