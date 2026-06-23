with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
match = re.search(r'def run_per_diem_check', content)
if match:
    start_pos = match.start()
    print("=== run_per_diem_check continuation 3 ===")
    print(content[start_pos+4500:start_pos+8000])
