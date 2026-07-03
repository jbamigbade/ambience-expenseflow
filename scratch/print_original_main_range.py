import sys

if len(sys.argv) < 3:
    print("Usage: python print_range.py <start> <end>")
    sys.exit(1)

start = int(sys.argv[1]) - 1
end = int(sys.argv[2])

with open("D:\\02_AI_and_Data\\Kaggle-AI-Agents\\Capstone\\scratch\\original_main.py", "r", encoding="utf-16") as f:
    content = f.read()

lines = content.splitlines()
for i in range(start, min(end, len(lines))):
    safe_line = lines[i].encode('ascii', errors='replace').decode('ascii')
    print(f"{i+1}: {safe_line}")
