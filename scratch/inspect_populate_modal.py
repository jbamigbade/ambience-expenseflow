with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer("function ", content)]
for m in matches:
    end = content.find(" {", m)
    func_sig = content[m:end].strip()
    if any(name in func_sig for name in ["Modal", "Review", "Compliance", "Show", "Detail"]):
        print(func_sig)
