import subprocess
import json

project = "project-5d38f91a-29a3-45bd-8d4"
filter_str = 'resource.type="pubsub_subscription" AND resource.labels.subscription_id="expense-reports-push"'

gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

res = subprocess.run([
    gcloud,
    "logging",
    "read",
    filter_str,
    f"--project={project}",
    "--format=json",
    "--limit=50"
], capture_output=True, text=True)

if res.returncode == 0:
    logs = json.loads(res.stdout)
    print(f"Found {len(logs)} log entries:")
    for log in logs[:10]:
        print(json.dumps(log, indent=2))
else:
    print("Error:", res.stderr)
