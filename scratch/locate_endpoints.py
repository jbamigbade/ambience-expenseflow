filepath = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

targets = [
    '/api/pending',
    '/api/expenses',
    '/api/employee/claims'
]

for idx, line in enumerate(lines):
    for t in targets:
        if f'"{t}"' in line or f"'{t}'" in line:
            print(f"Line {idx+1}: {line.strip()}")
