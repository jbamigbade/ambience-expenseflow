# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import uuid
from datetime import datetime
from google.cloud import firestore

# Ensure we can import from submission_frontend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "submission_frontend")))

# We will run the python-based helper functions to evaluate policies and recalculate totals
from main import run_policy_check_py, check_claim_missing_documents, recalculate_report_totals, add_report_audit_log

def main():
    PROJECT_ID = os.getenv("GCP_PROJECT", "project-5d38f91a-29a3-45bd-8d4")
    print(f"Connecting to Firestore for project: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)

    # 1. Ensure employee and manager are registered in the employees collection
    employee_email = "cra001.manager001@demo-company.com"
    manager_email = "manager001@demo-company.com"
    
    emp_ref = db.collection("employees").document(employee_email)
    emp_snap = emp_ref.get()
    if not emp_snap.exists:
        print(f"Employee {employee_email} does not exist in DB. Seeding...")
        emp_ref.set({
            "employee_email": employee_email,
            "employee_name": "CRA 001 Manager 001",
            "employee_id": "cra001.manager001",
            "department": "Clinical Research",
            "manager_email": manager_email,
            "company_id": "demo_company",
            "role_level": "employee",
            "active": True
        })
    else:
        print(f"Employee {employee_email} already exists in Firestore.")

    mget_ref = db.collection("employees").document(manager_email)
    if not mget_ref.get().exists:
        print(f"Manager {manager_email} does not exist. Seeding...")
        mget_ref.set({
            "employee_email": manager_email,
            "employee_name": "Manager 001",
            "employee_id": "manager001",
            "department": "Clinical Research",
            "manager_email": "finance_admin@demo-company.com",
            "company_id": "demo_company",
            "role_level": "manager",
            "active": True
        })

    # 2. Search for any existing draft report or create a new one
    reports_ref = db.collection("expense_reports")
    existing_reports = list(reports_ref.where("employee_email", "==", employee_email).where("report_title", "==", "April Site Visits").get())
    
    if existing_reports:
        # Let's delete existing demo reports to ensure clean verification run
        print(f"Cleaning up previous 'April Site Visits' report(s) to guarantee fresh end-to-end run.")
        for r_snap in existing_reports:
            r_id = r_snap.id
            print(f"Deleting previous report {r_id}...")
            # Delete claims
            claims = list(db.collection("expense_claims").where("report_id", "==", r_id).get())
            for c in claims:
                c.reference.delete()
            # Delete docs
            docs = list(db.collection("documents").where("report_id", "==", r_id).get())
            for d in docs:
                d.reference.delete()
            # Delete decisions
            decs = list(db.collection("report_decisions").where("report_id", "==", r_id).get())
            for dec in decs:
                dec.reference.delete()
            # Delete audits
            auds = list(db.collection("audit_logs").where("report_id", "==", r_id).get())
            for aud in auds:
                aud.reference.delete()
            # Delete report itself
            r_snap.reference.delete()

    # Create fresh report
    report_id = "rep_" + str(uuid.uuid4())[:18]
    print(f"Creating new draft Expense Report: '{report_id}'")
    report_data = {
        "company_id": "demo_company",
        "report_id": report_id,
        "employee_id": "cra001.manager001",
        "employee_email": employee_email,
        "employee_name": "CRA 001 Manager 001",
        "department": "Clinical Research",
        "manager_id": "manager001",
        "manager_email": manager_email,
        "report_title": "April Site Visits",
        "report_period_start": "2026-04-01",
        "report_period_end": "2026-04-30",
        "travel_week": None,
        "month": "04",
        "year": "2026",
        "status": "draft",
        "total_claimed_amount": 0.0,
        "total_reimbursable_amount": 0.0,
        "total_non_reimbursable_amount": 0.0,
        "claim_count": 0,
        "document_count": 0,
        "unassigned_document_count": 0,
        "missing_document_count": 0,
        "policy_exception_count": 0,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    db.collection("expense_reports").document(report_id).set(report_data)

    current_user = {
        "email": employee_email,
        "role": "employee",
        "name": "CRA 001 Manager 001",
        "authenticated": True
    }
    add_report_audit_log(report_id, None, "report_created", f"Created draft expense report 'April Site Visits'.", current_user)

    # 3. Add claims
    claims_to_add = [
        {"category": "flight", "amount": 1350.0, "purpose": "Site visit flight"},
        {"category": "hotel", "amount": 700.0, "purpose": "Site visit hotel stay"},
        {"category": "meals", "amount": 300.0, "purpose": "Meals during site visits"},
        {"category": "rental_car", "amount": 320.0, "purpose": "Rental car for site commutes"},
        {"category": "rental_car_gas", "amount": 65.0, "purpose": "Rental car fuel"},
        {"category": "parking", "amount": 40.0, "purpose": "Parking fees"},
        {"category": "mileage", "amount": 120.0, "purpose": "Personal car local commute mileage"},
    ]

    claim_ids = {}
    for c in claims_to_add:
        claim_id = "clm_" + str(uuid.uuid4())[:18]
        claim_ids[c["category"]] = claim_id
        
        claim_doc = {
            "company_id": "demo_company",
            "report_id": report_id,
            "claim_id": claim_id,
            "employee_id": "cra001.manager001",
            "employee_email": employee_email,
            "employee_name": "CRA 001 Manager 001",
            "manager_email": manager_email,
            "category": c["category"],
            "amount": c["amount"],
            "currency": "USD",
            "expense_date": "2026-04-10",
            "business_purpose": c["purpose"],
            "description": c["purpose"],
            "claim_status": "draft",
            "reimbursable_amount": c["amount"],
            "non_reimbursable_amount": 0.0,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Calculate policies and missing docs initially (which will flag missing docs)
        claim_doc = check_claim_missing_documents(report_id, claim_doc)
        db.collection("expense_claims").document(claim_id).set(claim_doc)
        add_report_audit_log(report_id, claim_id, "claim_added_to_report", f"Added claim item for {c['category']} ($ {c['amount']})", current_user)

    print("Line items successfully added as drafts.")

    # Recalculate totals after adding line items
    recalculate_report_totals(report_id)
    rep_snap = db.collection("expense_reports").document(report_id).get().to_dict()
    print(f"Draft report totals: claimed={rep_snap['total_claimed_amount']}, missing_docs={rep_snap['missing_document_count']}, exceptions={rep_snap['policy_exception_count']}")

    # 4. Upload receipts and assign them to satisfy required documents
    # The flight of $1350 requires TWO docs: "Flight Ticket Receipt" and "Manager Approval Letter".
    print("Uploading and assigning required receipts...")
    
    # Upload Flight Ticket Receipt
    f_rec_id = "doc_" + str(uuid.uuid4())[:18]
    db.collection("documents").document(f_rec_id).set({
        "company_id": "demo_company",
        "report_id": report_id,
        "claim_id": claim_ids["flight"],
        "document_id": f_rec_id,
        "doc_type": "flight_ticket_receipt",
        "file_name": "flight_e_ticket.pdf",
        "gcs_path": f"gs://expense-manager-uploads-654812449031/uploads/reports/{report_id}/{f_rec_id}/flight_e_ticket.pdf",
        "assigned_to_claim": True,
        "uploaded_by_email": employee_email,
        "uploaded_by_role": "employee",
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "active": True
    })
    add_report_audit_log(report_id, claim_ids["flight"], "document_assigned_to_claim", f"Uploaded and assigned 'flight_e_ticket.pdf' to flight claim.", current_user)

    # Upload Manager Approval Letter
    m_let_id = "doc_" + str(uuid.uuid4())[:18]
    db.collection("documents").document(m_let_id).set({
        "company_id": "demo_company",
        "report_id": report_id,
        "claim_id": claim_ids["flight"],
        "document_id": m_let_id,
        "doc_type": "manager_approval_letter",
        "file_name": "pre_approval_signed.pdf",
        "gcs_path": f"gs://expense-manager-uploads-654812449031/uploads/reports/{report_id}/{m_let_id}/pre_approval_signed.pdf",
        "assigned_to_claim": True,
        "uploaded_by_email": employee_email,
        "uploaded_by_role": "employee",
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "active": True
    })
    add_report_audit_log(report_id, claim_ids["flight"], "document_assigned_to_claim", f"Uploaded and assigned 'pre_approval_signed.pdf' to flight claim.", current_user)

    # Run checks and recalculations again
    for c_id in claim_ids.values():
        c_ref = db.collection("expense_claims").document(c_id)
        c_doc = c_ref.get().to_dict()
        c_doc = check_claim_missing_documents(report_id, c_doc)
        c_ref.set(c_doc)

    recalculate_report_totals(report_id)
    rep_snap = db.collection("expense_reports").document(report_id).get().to_dict()
    print(f"Totals after receipt assignments: claimed={rep_snap['total_claimed_amount']}, missing_docs={rep_snap['missing_document_count']}, exceptions={rep_snap['policy_exception_count']}")

    # 5. Submit the report
    print("Submitting the report for manager review...")
    db.collection("expense_reports").document(report_id).update({
        "status": "pending_manager_review",
        "submitted_by_email": employee_email,
        "submitted_by_role": "employee",
        "submitted_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    })
    add_report_audit_log(report_id, None, "report_submitted", "Expense report 'April Site Visits' submitted for manager review.", current_user)

    # 6. Manager reviews and approves the report
    manager_user = {
        "email": manager_email,
        "role": "manager",
        "name": "Manager 001",
        "authenticated": True
    }
    print("Manager approving the report...")
    db.collection("expense_reports").document(report_id).update({
        "status": "approved_by_manager",
        "manager_reviewed_by": manager_email,
        "manager_reviewed_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    })
    
    # Update individual claims status to approved
    claims = list(db.collection("expense_claims").where("report_id", "==", report_id).get())
    for c_snap in claims:
        c_snap.reference.update({"claim_status": "approved"})

    dec_id = "dec_" + str(uuid.uuid4())[:18]
    db.collection("report_decisions").document(dec_id).set({
        "company_id": "demo_company",
        "report_id": report_id,
        "claim_id": None,
        "decision_id": dec_id,
        "decision_scope": "report",
        "decision": "approved",
        "reason": "Full report approved. All receipts validated.",
        "actor_email": manager_email,
        "actor_role": "manager",
        "authenticated": True,
        "decided_at": datetime.utcnow().isoformat() + "Z"
    })
    add_report_audit_log(report_id, None, "manager_decision", "Expense report approved by manager.", manager_user)

    print("\n=======================================================")
    print("             DEMO WORKFLOW RUN COMPLETED               ")
    print("=======================================================")
    final_rep = db.collection("expense_reports").document(report_id).get().to_dict()
    print(f"Report Title:    {final_rep['report_title']}")
    print(f"Report ID:       {final_rep['report_id']}")
    print(f"Employee Email:  {final_rep['employee_email']}")
    print(f"Status:          {final_rep['status']}")
    print(f"Claimed Amount:  ${final_rep['total_claimed_amount']}")
    print(f"Reimbursable:    ${final_rep['total_reimbursable_amount']}")
    print(f"Missing Docs:    {final_rep['missing_document_count']}")
    print(f"Policy Exception:{final_rep['policy_exception_count']}")
    print(f"Submitted At:    {final_rep['submitted_at']}")
    print(f"Reviewed By:     {final_rep['manager_reviewed_by']}")
    print(f"Reviewed At:     {final_rep['manager_reviewed_at']}")
    print("\n---------------- AUDIT TRAIL TIMELINE ----------------")
    
    audits_list = list(db.collection("audit_logs").where("report_id", "==", report_id).get())
    audits_data = [aud.to_dict() for aud in audits_list]
    audits_sorted = sorted(audits_data, key=lambda x: x.get("created_at", ""))
    for a in audits_sorted:
        print(f"[{a['created_at']}] ({a['event_type']}) {a['actor_role']}: {a['message']}")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
