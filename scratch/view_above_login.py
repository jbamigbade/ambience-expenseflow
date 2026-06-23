with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx in range(2700, min(2790, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")
