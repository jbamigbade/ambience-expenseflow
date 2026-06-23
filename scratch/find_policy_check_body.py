with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
for idx, line in enumerate(lines):
    if "def run_policy_check_py" in line:
        start_idx = idx
        break

if start_idx != -1:
    print(f"Found run_policy_check_py starting at line {start_idx + 1}")
    for idx in range(start_idx, start_idx + 115):
        print(f"Line {idx+1}: {lines[idx].rstrip()}")
else:
    print("Not found")
