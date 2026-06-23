with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if '/api/upload/{session_id}' in line:
        print("".join(lines[idx:idx+80]))
        break
