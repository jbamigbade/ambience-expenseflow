with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer("function ", content)]
js_funcs = []
for m in matches:
    end = content.find("\n", m)
    line = content[m:end].strip()
    if "{" in line:
        line = line[:line.find("{")].strip()
    # If the function is after line 2481 (which is part of html_content)
    if m > 108455:
        js_funcs.append((m, line))

print("Found JS Functions:")
for pos, f in js_funcs:
    print(f"  Pos {pos}: {f}")
