import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== API EXPENSES 1820 - 1862 ===")
for idx in range(1819, min(1862, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")
