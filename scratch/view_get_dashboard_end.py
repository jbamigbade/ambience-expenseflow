import sys

with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

found = False
for idx, line in enumerate(lines):
    if "async def get_dashboard" in line:
        # scan for the return statement of this function
        for j in range(idx+1, len(lines)):
            if "return HTMLResponse(" in lines[j] or "return" in lines[j] and "HTMLResponse" in "".join(lines[j:j+10]):
                content = "".join(lines[j-20:j+20])
                sys.stdout.buffer.write(content.encode("utf-8"))
                found = True
                break
        if found:
            break
