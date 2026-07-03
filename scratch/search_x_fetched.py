import urllib.request
import re

url = "http://127.0.0.1:8080/"
with urllib.request.urlopen(url) as response:
    html = response.read().decode('utf-8')

lines = html.splitlines()
for i, line in enumerate(lines):
    # Search for any lone letter 'x' or a stray 'x' that's not part of standard CSS/JS/HTML words.
    # We can match word boundaries but exclude tag attributes.
    if re.search(r'\bx\b', line) or line.strip() == 'x' or line.strip() == 'x':
        print(f"Line {i+1}: {repr(line)}")
