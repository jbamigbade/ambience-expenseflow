with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'id="tab-submit"' in line or 'class="tabs"' in line:
        print(f"Found on line {i+1}: {line.strip()}")
        for j in range(max(0, i - 5), min(i + 25, len(lines))):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
