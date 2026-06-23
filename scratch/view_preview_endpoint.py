import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== PREVIEW API ENDPOINT 2520 - 2555 ===")
for idx in range(2519, min(2555, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")
