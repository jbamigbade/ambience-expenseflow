import os

def find_literal_backslash_n():
    for root, dirs, files in os.walk('submission_frontend'):
        for file in files:
            if file.endswith(('.html', '.js', '.py')):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f):
                            if '\\n' in line:
                                print(f"{path}:{i+1}: {repr(line)}")
                except Exception as e:
                    print(f"Error reading {path}: {e}")

if __name__ == '__main__':
    find_literal_backslash_n()
