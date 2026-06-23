with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
print("Searching for currentUser or role in script block:")
for m in re.finditer(r'(role|currentUser|current_user|email)', content, re.IGNORECASE):
    # Only search within <script>...</script>
    # Find script index
    script_start = content.find("<script>")
    script_end = content.find("</script>")
    if script_start <= m.start() <= script_end:
        start = max(script_start, m.start() - 50)
        end = min(script_end, m.end() + 150)
        print(f"Index {m.start()}: {content[start:end]}\n---")
