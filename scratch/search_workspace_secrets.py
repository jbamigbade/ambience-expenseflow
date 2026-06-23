# Search workspace for files containing Google OAuth Client ID or Secret
import os

keywords = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'Client ID', 'Client Secret']
ignore_dirs = ['.git', '.venv', '__pycache__', '.pytest_cache', 'submission_frontend']

found = []
for root, dirs, files in os.walk('.'):
    # modify dirs in place to ignore specific directories
    dirs[:] = [d for dirs_val in [dirs] for d in dirs_val if d not in ignore_dirs]
    for file in files:
        if file.endswith('.py') or file.endswith('.json') or file.endswith('.yaml') or file.endswith('.txt') or file.endswith('.md'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for kw in keywords:
                        if kw in content:
                            found.append((path, kw))
            except Exception:
                pass

print("Search results:")
for path, kw in found:
    print(f"File: {path} contains keyword: {kw}")
