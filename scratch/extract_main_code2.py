with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Let's locate the `@app.post("/api/ingest-expense")` and grab more characters
import re
match = re.search(r'@app\.post\("/api/ingest-expense"\)', content)
if match:
    start_pos = match.start()
    print("=== API Ingest Expense continuation ===")
    print(content[start_pos+1500:start_pos+6000])

match2 = re.search(r'def find_and_bind_expense', content)
if match2:
    start_pos2 = match2.start()
    print("\n=== find_and_bind_expense continuation ===")
    print(content[start_pos2+1000:start_pos2+3500])
