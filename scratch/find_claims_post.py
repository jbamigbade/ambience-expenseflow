with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, 1):
        if "/claims" in line and "@app.post" in line:
            print(idx, line.strip())
