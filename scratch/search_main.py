with open('submission_frontend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

patterns = [
    '</style>',
    'section-pending',
    'reports-grid',
    'fetchPendingApprovals',
    'pendingSourceFilter',
    'section-reports',
    'new-report-form',
    'create-report-container',
    'renderReportsGrid'
]

for i, line in enumerate(lines):
    line_num = i + 1
    for pat in patterns:
        if pat in line:
            print(f"[{pat}] Line {line_num}: {line.strip()[:100]}")
