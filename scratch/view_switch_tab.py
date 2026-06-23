with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "function switchTab" in line:
        print(f"Found switchTab at line {i+1}")
        for j in range(max(0, i - 10), min(i + 50, len(lines))):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
