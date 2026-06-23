with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "function switchTab" in line:
        print(f"Line {idx+1}: {line.strip()[:100]}")
        # print the next 40 lines
        for j in range(idx, min(idx + 40, len(lines))):
            print(f"  Line {j+1}: {lines[j].rstrip()}")
        break
