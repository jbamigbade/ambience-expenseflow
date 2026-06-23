import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== GET_DASHBOARD STRUCTURE 2935 - 2975 ===")
for idx in range(2934, min(2975, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")
