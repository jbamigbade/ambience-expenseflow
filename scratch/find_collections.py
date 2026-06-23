with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "_COL =" in line or "db.collection" in line:
            print(f"Line {idx+1}: {line.strip()}")
