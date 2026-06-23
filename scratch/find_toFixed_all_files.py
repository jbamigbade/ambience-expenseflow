import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

root_dir = r"C:\Users\johnb\ambient-expense-agent"

for dirpath, dirnames, filenames in os.walk(root_dir):
    # Skip .venv, .git, .pytest_cache, etc.
    if any(p in dirpath for p in [".venv", ".git", ".pytest_cache", ".google-agents-cli", "__pycache__", ".agents", "artifacts", "scratch"]):
        continue
    for filename in filenames:
        if filename.endswith((".py", ".js", ".html", ".css", ".ts")):
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                if ".toFixed" in content:
                    print(f"Found in {filepath}")
            except Exception as e:
                pass
