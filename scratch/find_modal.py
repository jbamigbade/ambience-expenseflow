with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer("toggleModal", content)]
print(f"toggleModal found {len(matches)} times.")
for m in matches[:5]:
    start = max(0, m - 100)
    end = min(len(content), m + 200)
    snippet = content[start:end]
    print(f"Snippet: ... {snippet.encode('ascii', errors='replace').decode('ascii')} ...\n")
