with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "def run_per_diem_check" in line:
            print(f"Line {idx+1}: {line.strip()}")
            break
