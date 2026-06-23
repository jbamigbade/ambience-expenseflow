import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'id="slide' in line or 'class="slide' in line or 'toggleModal' in line or 'class="modal' in line:
        print(f"Line {idx+1}: {line.strip()[:120]}")
