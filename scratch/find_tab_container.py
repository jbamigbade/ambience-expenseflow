with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if 'id="tab-pending"' in line or 'id="tab-history"' in line:
            print(f"Line {idx+1}: {line.strip()}")
