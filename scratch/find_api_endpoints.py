with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if '/api/' in line and ('@app.get' in line or '@app.post' in line):
            print(f"Line {idx}: {line.strip()}")
