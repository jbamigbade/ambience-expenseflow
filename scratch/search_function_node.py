with open(r"C:\Users\johnb\ambient-expense-agent\.venv\Lib\site-packages\google\adk\workflow\_function_node.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer(r"adk_request_input|RequestInput", content)]
print("Found", len(matches), "matches")
for m in matches:
    start = max(0, m - 150)
    end = min(len(content), m + 150)
    print(f"\n--- MATCH AT {m} ---")
    print(content[start:end])
