import re

file_path = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"

queries = [
    r"db = firestore\.client",
    r"initialize_app"
]

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for q in queries:
    pattern = re.compile(q, re.IGNORECASE)
    print(f"=== Matches for query: {q} ===")
    for idx, line in enumerate(lines):
        if pattern.search(line):
            print(f"Line {idx+1}: {line.strip()}")
    print()
