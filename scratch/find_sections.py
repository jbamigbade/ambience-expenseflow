with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer('id="section-pending"', content)]
if matches:
    pos = matches[0]
    print(f"section-pending found at char {pos}")
    # print the next 2000 chars
    print(content[pos-50:pos+2000])
