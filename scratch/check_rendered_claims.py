import urllib.request

url = "http://127.0.0.1:8080/"
with urllib.request.urlopen(url) as response:
    html = response.read().decode('utf-8')

lines = html.splitlines()
for i in range(725, 760):
    if i < len(lines):
        print(f"{i+1}: {repr(lines[i])}")
