import os
import re

search_dir = r"C:\Users\johnb\ambient-expense-agent\.venv\Lib\site-packages\google\adk"
pattern = re.compile(r"resume_inputs")

for root, dirs, files in os.walk(search_dir):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "resume_inputs" in content:
                print(f"File: {os.path.relpath(path, search_dir)}")
                for idx, line in enumerate(content.splitlines()):
                    if "resume_inputs" in line:
                        print(f"  {idx+1}: {line.strip()}")
