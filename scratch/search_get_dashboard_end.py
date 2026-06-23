with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
for idx, line in enumerate(lines):
    if "async def get_dashboard" in line:
        start_idx = idx
        break

if start_idx != -1:
    print(f"get_dashboard starts at line {start_idx + 1}")
    # Search backwards from the end of the file or lines below start_idx for return HTMLResponse
    for idx in range(start_idx + 1500, len(lines)): # wait, get_dashboard might be 2000 lines long!
        if "return HTMLResponse" in lines[idx]:
            print(f"Found return HTMLResponse at line {idx + 1}")
            for j in range(idx - 50, min(idx + 10, len(lines))):
                print(f"Line {j+1}: {lines[j].rstrip()}")
            break
