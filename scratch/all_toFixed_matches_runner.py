import sys

sys.stdout.reconfigure(encoding='utf-8')

filepath = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

output_file = r"C:\Users\johnb\ambient-expense-agent\scratch\all_toFixed_matches.txt"
with open(output_file, "w", encoding="utf-8") as out:
    for idx, line in enumerate(lines):
        if ".toFixed" in line:
            out.write(f"Line {idx+1}: {line.strip()}\n")

print(f"Wrote all matches to {output_file}")
