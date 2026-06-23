import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== POLICY RULES 500 - 650 ===")
for idx in range(499, min(650, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")
