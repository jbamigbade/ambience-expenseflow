import re

with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find all script block contents
scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
print(f"Found {len(scripts)} script blocks.")

# For each script block, print all function definitions
for i, script in enumerate(scripts):
    print(f"\n--- Script Block {i+1} ---")
    funcs = re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', script)
    print(f"Functions defined ({len(funcs)}): {funcs}")
    
    # Also look for arrow function variables: const name = (...) =>
    arrows = re.findall(r'(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>', script)
    print(f"Arrow functions defined ({len(arrows)}): {arrows}")
