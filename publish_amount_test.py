import json
import subprocess
import sys

project = "project-5d38f91a-29a3-45bd-8d4"
topic = "expense-reports"
gcloud = r"C:\Users\johnb\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

amount = float(sys.argv[1])
submitter = f"test.amount.{int(amount)}@company.com"

payload = {
    "employee_name": submitter,
    "amount": amount,
    "description": f"Dashboard amount test ${amount}"
}

message = json.dumps({
    "input": {
        "message": json.dumps(payload),
        "user_id": "default-user"
    }
})

print("Publishing test expense:")
print(message)

subprocess.run([
    gcloud,
    "pubsub",
    "topics",
    "publish",
    topic,
    f"--project={project}",
    f"--message={message}"
], check=True)
