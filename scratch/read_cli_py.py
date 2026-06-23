with open(r"C:\Users\johnb\ambient-expense-agent\.venv\Lib\site-packages\google\adk\cli\cli.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx in range(690, 730):
    print(f"{idx+1}: {lines[idx].strip()}")
