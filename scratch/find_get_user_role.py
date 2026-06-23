with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "def get_current_user_and_role" in line:
            print(f"Line {idx+1}: {line.strip()}")
            break
