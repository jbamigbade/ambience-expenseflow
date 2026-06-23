import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer('<div class="slide-modal"', content)]
if matches:
    pos = matches[0]
    print(content[pos+1400:pos+3000])
