import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== CREATE CLAIM API ENDPOINT 2154 - 2250 ===")
for idx in range(2153, min(2250, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")
