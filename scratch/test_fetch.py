import urllib.request

def fetch_and_analyze():
    try:
        url = "http://127.0.0.1:8080/"
        print(f"Fetching {url}...")
        with urllib.request.urlopen(url) as response:
            html = response.read().decode('utf-8')
            
        print("Fetched successfully. Content length:", len(html))
        
        # Look for physical newline vs literal backslash-n
        print("Literal \\n count in HTML:", html.count("\\n"))
        
        lines = html.splitlines()
        for i, line in enumerate(lines):
            if "\\n" in line:
                print(f"Line {i+1}: {repr(line)}")
                
            # Look for stray 'x'
            if "New Expense Report" in line:
                print(f"Found 'New Expense Report' around line {i+1}:")
                for j in range(max(0, i-5), min(len(lines), i+6)):
                    safe_line = lines[j].encode('ascii', errors='replace').decode('ascii')
                    print(f"  {j+1}: {repr(safe_line)}")
                    
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    fetch_and_analyze()
