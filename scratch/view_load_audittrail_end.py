import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== LOADAUDITTRAIL JS 4060 - 4110 ===")
for idx in range(4059, min(4110, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")
