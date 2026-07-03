with open('submission_frontend/static/js/dashboard.js', 'r', encoding='utf-8') as f:
    content = f.read()

stack = []
mapping = {')': '(', '}': '{', ']': '['}
lines = content.splitlines()

for i, line in enumerate(lines):
    in_string = False
    string_char = None
    in_comment = False
    in_block_comment = False
    j = 0
    while j < len(line):
        if in_comment:
            break
        if in_block_comment:
            if line[j:j+2] == '*/':
                in_block_comment = False
                j += 2
                continue
            j += 1
            continue
        
        # string check
        if in_string:
            if line[j] == '\\':
                j += 2
                continue
            if line[j] == string_char:
                in_string = False
            j += 1
            continue
            
        # check comments
        if line[j:j+2] == '//':
            break
        if line[j:j+2] == '/*':
            in_block_comment = True
            j += 2
            continue
            
        # string start
        if line[j] in ["'", '"', '`']:
            in_string = True
            string_char = line[j]
            j += 1
            continue
            
        char = line[j]
        if char in '({[':
            stack.append((char, i+1, j+1))
        elif char in ')}]':
            if not stack:
                print(f'Mismatched closing {char} on line {i+1}, column {j+1}')
            else:
                top, l, col = stack.pop()
                if top != mapping[char]:
                    print(f'Mismatched closing {char} on line {i+1}, column {j+1} (expected {mapping[char]} from line {l}, col {col})')
        j += 1

if stack:
    print(f'Unclosed brackets left on stack: {len(stack)}')
    for item in stack[:10]:
        print(f'  Unclosed {item[0]} from line {item[1]}, column {item[2]}')
else:
    print('All simple braces balanced.')
