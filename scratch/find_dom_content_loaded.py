with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "DOMContentLoaded" in line:
        print(f"Found DOMContentLoaded at line {i+1}")
        for j in range(max(0, i - 5), min(i + 30, len(lines))):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
