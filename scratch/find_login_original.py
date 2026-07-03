with open('scratch/original_main.py', 'r', encoding='utf-16') as f:
    lines = f.readlines()

found = False
for i, line in enumerate(lines):
    if '@app.get("/login"' in line or 'async def get_login' in line:
        print(f"Line {i+1}: {line.strip().encode('ascii', errors='replace').decode('ascii')}")
        found = True
        for j in range(max(0, i-2), min(len(lines), i+80)):
            safe_l = lines[j].rstrip().encode('ascii', errors='replace').decode('ascii')
            print(f"  {j+1}: {safe_l}")
        break

if not found:
    print("Not found with exact pattern.")
