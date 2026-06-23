import subprocess
import json
import re
import sys

def run_cmd(cmd):
    print(f"Executing command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    print("--- STDOUT ---")
    print(result.stdout)
    print("--- STDERR ---")
    print(result.stderr)
    return result.stdout, result.stderr

def main():
    url = "https://us-west1-aiplatform.googleapis.com/v1beta1/projects/project-5d38f91a-29a3-45bd-8d4/locations/us-west1/reasoningEngines/8516245322706452480"
    
    print("======================================================================")
    print("TEST CASE 1: Standard Meal Expense ($50.00)")
    print("======================================================================")
    claim_50 = '{"employee_name": "Alice Smith", "amount": 50.00, "description": "Team lunch"}'
    cmd_50 = [
        "uv", "run", "agents-cli", "run",
        "--url", url,
        "--mode", "adk",
        "-v",
        claim_50
    ]
    stdout_50, _ = run_cmd(cmd_50)
    
    if "automatically approved" in stdout_50:
        print("[PASS] Test Case 1: Standard Meal Expense automatically approved!")
    else:
        print("[FAIL] Test Case 1: Standard Meal Expense auto-approval not found in response.")
        sys.exit(1)

    print("\n======================================================================")
    print("TEST CASE 2 - Step 1: Client Dinner Expense ($150.00) - HITL Pause")
    print("======================================================================")
    claim_150 = '{"employee_name": "Bob Jones", "amount": 150.00, "description": "Client dinner"}'
    cmd_150 = [
        "uv", "run", "agents-cli", "run",
        "--url", url,
        "--mode", "adk",
        "-v",
        claim_150
    ]
    stdout_150, _ = run_cmd(cmd_150)
    
    # In verbose mode, the interrupt prompt is inside the adk_request_input function call payload
    if "adk_request_input" in stdout_150 and "ATTENTION REQUIRED" in stdout_150:
        print("[PASS] Test Case 2 Step 1: Human-in-the-loop pause triggered successfully!")
    else:
        print("[FAIL] Test Case 2 Step 1: HITL pause not triggered or adk_request_input event missing.")
        sys.exit(1)

    # Extract session ID from the output
    session_id_match = re.search(r"Session:\s*(\d+)", stdout_150)
    if not session_id_match:
        print("[FAIL] Could not parse Session ID from the remote output.")
        sys.exit(1)
        
    session_id = session_id_match.group(1)
    print(f"\nSuccessfully parsed Session ID: {session_id}")

    print("\n======================================================================")
    print("TEST CASE 2 - Step 2: Resume Session with 'approve' (Approval Verification)")
    print("======================================================================")
    cmd_resume = [
        "uv", "run", "agents-cli", "run",
        "--url", url,
        "--mode", "adk",
        "-v",
        "--session-id", session_id,
        "approve"
    ]
    stdout_resume, _ = run_cmd(cmd_resume)
    
    if "approved by human reviewer" in stdout_resume:
        print("[PASS] Test Case 2 Step 2: Resumed session and successfully approved expense!")
    else:
        print("[FAIL] Test Case 2 Step 2: Expense approval not verified in resumed session.")
        sys.exit(1)

    print("\n======================================================================")
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("======================================================================")

if __name__ == "__main__":
    main()
