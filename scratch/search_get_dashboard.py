with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "async def get_dashboard" in line:
        print(f"Line {idx+1}: {line.strip()[:120]}")
        # print 80 lines
        for j in range(idx, min(idx + 100, len(lines))):
            if "html_content = " in lines[j] or "rendered_content = " in lines[j] or "replace" in lines[j] or "return" in lines[j]:
                print(f"  Line {j+1}: {lines[j].strip()[:120]}")
        break
