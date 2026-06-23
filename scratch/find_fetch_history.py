with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer("function fetchExpenseHistory", content)]
if matches:
    pos = matches[0]
    print(f"fetchExpenseHistory found at char {pos}")
    snippet = content[pos:pos+1500]
    print(snippet.encode("ascii", errors="replace").decode("ascii"))
