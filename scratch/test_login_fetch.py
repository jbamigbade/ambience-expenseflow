import urllib.request

def fetch_login():
    try:
        url = "http://127.0.0.1:8080/login"
        print(f"Fetching {url}...")
        with urllib.request.urlopen(url) as response:
            html = response.read().decode('utf-8')
            
        print("Fetched successfully. Content length:", len(html))
        print("Contains 'Sign in with Google':", "Sign in with Google" in html)
        print("Contains 'Local Test Mode Active':", "Local Test Mode Active" in html)
        print("Contains 'Enter Dashboard':", "Enter Dashboard" in html)
        
        # Print a snippet of the buttons
        lines = html.splitlines()
        for i, line in enumerate(lines):
            if "btn-google" in line or "btn-bypass" in line or "badge-dev" in line:
                print(f"Line {i+1}: {repr(line)}")
                    
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    fetch_login()
