with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
keywords = ["mileage", "rental", "gas", "personal_vehicle", "transportation_type", "business_miles"]
for kw in keywords:
    matches = [m.start() for m in re.finditer(kw, content, re.IGNORECASE)]
    print(f"Keyword '{kw}': {len(matches)} matches")
    for m in matches[:5]:
        start = max(0, m - 50)
        end = min(len(content), m + 100)
        snippet = content[start:end].replace("\n", " ")
        print(f"  Snippet: ... {snippet} ...")
