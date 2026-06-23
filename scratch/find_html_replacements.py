import re

file_path = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"

queries = [
    r"hide_old",
    r"hide-old",
    r"old-test",
    r"hide",
    r"old",
    r"filter",
    r"assigned_to_me"
]

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for q in queries:
    pattern = re.compile(q, re.IGNORECASE)
    print(f"=== Matches for query: {q} ===")
    matches = 0
    for idx, line in enumerate(lines):
        if pattern.search(line):
            print(f"Line {idx+1}: {line.strip()}")
            matches += 1
            if matches >= 10:
                print("... truncated matches ...")
                break
    print()
