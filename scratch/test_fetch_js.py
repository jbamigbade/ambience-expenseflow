import urllib.request

url = "http://127.0.0.1:8080/static/js/dashboard.js"
print("Fetching JS from", url)
try:
    with urllib.request.urlopen(url) as response:
        js_content = response.read().decode('utf-8')
    print("JS fetched successfully. Length:", len(js_content))
    
    lines = js_content.splitlines()
    for i, line in enumerate(lines):
        if "\\n\\n" in line or "\\n" in line:
            # exclude acceptable JS \n sequences inside strings
            if i+1 in [1954, 2924]:
                print(f"Line {i+1}: {repr(line)}")
except Exception as e:
    print("Error:", e)
