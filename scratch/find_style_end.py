with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer(r'</style>', content)]
print(f"Found </style> at positions: {matches}")
for m in matches:
    # Convert position to line number
    line_num = content[:m].count("\n") + 1
    print(f"Line {line_num}: {content[m:m+50].strip()}")
