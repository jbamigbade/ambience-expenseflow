with open(r"C:\Users\johnb\ambient-expense-agent\.venv\Lib\site-packages\vertexai\agent_engines\templates\adk.py", "r", encoding="utf-8") as f:
    content = f.read()

import re

# Find occurrences of "adk_request_input" or "resume_inputs" or "RequestInput"
for m in re.finditer(r"(adk_request_input|resume_inputs|RequestInput)", content):
    start = max(0, m.start() - 100)
    end = min(len(content), m.end() + 100)
    print(f"--- MATCH AT {m.start()} ---")
    print(content[start:end])
