with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
match = re.search(r'def run_policy_check_py', content)
if match:
    start_pos = match.start()
    print("=== run_policy_check_py ===")
    print(content[start_pos:start_pos+3500])
