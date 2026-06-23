with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
match = re.search(r'def parse_claim_from_session', content)
if match:
    start_pos = match.start()
    print("=== parse_claim_from_session ===")
    print(content[start_pos:start_pos+3500])
