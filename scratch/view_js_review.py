import sys

with open(r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
# Look for functions that deal with the modal, e.g. toggleModal, openModal, showModal, review, claim
matches = list(re.finditer(r'function \w*(?:modal|review|claim)\w*', content, re.IGNORECASE))
for m in matches:
    start = max(0, m.start() - 50)
    end = min(len(content), m.end() + 600)
    sys.stdout.buffer.write(f"--- MATCH ---\n".encode("utf-8"))
    sys.stdout.buffer.write(content[start:end].encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
