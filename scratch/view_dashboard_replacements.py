import sys

with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "def get_dashboard" in line:
        for j in range(idx+1, len(lines)):
            if "return HTMLResponse(" in lines[j] or "return" in lines[j] and "HTMLResponse" in "".join(lines[j:j+10]):
                content = "".join(lines[j-130:j+5])
                sys.stdout.buffer.write(content.encode("utf-8"))
                break
        break
