with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "LOGIN_HTML =" in line:
        print(f"Line {idx+1}: {line.strip()}")
        break
