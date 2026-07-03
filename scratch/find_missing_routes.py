with open('scratch/original_main.py', 'r', encoding='utf-16') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if any(pattern in line for pattern in ['/chat', 'feedback', 'stream']):
        if '@app.' in line or 'async def' in line:
            print(f"Line {i+1}: {line.strip()}")
