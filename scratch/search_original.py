# Search original_main.py in UTF-16
import sys
import os

path = "D:\\02_AI_and_Data\\Kaggle-AI-Agents\\Capstone\\scratch\\original_main.py"
if not os.path.exists(path):
    print("Not found")
    sys.exit(1)

query = sys.argv[1] if len(sys.argv) > 1 else "AUTH_ENABLED"
print(f"Searching for: '{query}'")

with open(path, "r", encoding="utf-16") as f:
    content = f.read()

lines = content.splitlines()
matches = 0
for i, line in enumerate(lines):
    if query in line:
        matches += 1
        print(f"Line {i+1}: {line.strip()[:150]}")
        # Print context
        start = max(0, i-2)
        end = min(len(lines), i+3)
        for j in range(start, end):
            prefix = "-> " if j == i else "   "
            print(f"{prefix}{j+1}: {lines[j]}")
        print("-" * 40)
        if matches >= 10:
            print("Truncated further matches")
            break
