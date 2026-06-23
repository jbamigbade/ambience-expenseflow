import re

with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Let's search for "/api/ingest-expense"
match = re.search(r'@app\.post\("/api/ingest-expense"\)', content)
if match:
    start_pos = match.start()
    # Let's print the next 2000 characters
    print("=== API Ingest Expense ===")
    print(content[start_pos:start_pos+3000])

# Let's search for "find_and_bind_expense"
match = re.search(r'def find_and_bind_expense', content)
if match:
    start_pos = match.start()
    print("\n=== find_and_bind_expense ===")
    print(content[start_pos:start_pos+3000])
