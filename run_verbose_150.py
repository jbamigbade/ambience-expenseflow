import subprocess

def main():
    result = subprocess.run([
        "uv", "run", "agents-cli", "run",
        "--url", "https://us-west1-aiplatform.googleapis.com/v1beta1/projects/project-5d38f91a-29a3-45bd-8d4/locations/us-west1/reasoningEngines/8516245322706452480",
        "--mode", "adk",
        "-v",
        '{"employee_name": "Bob Jones", "amount": 150.00, "description": "Client dinner"}'
    ], capture_output=True, text=True, encoding="utf-8")
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)

if __name__ == "__main__":
    main()
