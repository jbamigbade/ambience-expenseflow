with open(r"C:\Users\johnb\ambient-expense-agent\.venv\Lib\site-packages\google\adk\runners.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx in range(639, 680):
    if idx < len(lines):
        print(f"{idx+1}: {lines[idx].strip()}")
