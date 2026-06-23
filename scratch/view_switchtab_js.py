import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== SWITCH TAB JS 3840 - 3915 ===")
for idx in range(3839, min(3915, len(lines))):
    print(f"Line {idx+1}: {lines[idx].rstrip()}")
