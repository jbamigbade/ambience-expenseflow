import re

filepath = r"C:\Users\johnb\ambient-expense-agent\submission_frontend\main.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Let's search for FastAPI routes, e.g., @app.get, @app.post
routes = re.findall(r"@app\.(get|post|put|delete)\(\"([^\"]+)\"\)", content)
for r in routes:
    print(r)
