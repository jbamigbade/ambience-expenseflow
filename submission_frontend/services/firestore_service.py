from google.cloud import firestore
from submission_frontend.config.settings import PROJECT_ID, logger

_real_db = None

def seed_demo_employees(target_db):
    if not target_db:
        return
    try:
        employees = [
            {
                "employee_name": "Fresh Manager Test",
                "employee_email": "fresh.manager.test@company.com",
                "department": "Operations",
                "manager_email": "obamigbade@gmail.com",
                "company_id": "demo_company",
                "role_level": "employee",
                "active": True
            },
            {
                "employee_name": "Receipt Test",
                "employee_email": "receipt.test@company.com",
                "department": "Finance",
                "manager_email": "obamigbade@gmail.com",
                "company_id": "demo_company",
                "role_level": "employee",
                "active": True
            },
            {
                "employee_name": "Auth Hotel Docs Test",
                "employee_email": "auth.hotel.docs.test@company.com",
                "department": "Sales",
                "manager_email": "obamigbade@gmail.com",
                "company_id": "demo_company",
                "role_level": "employee",
                "active": True
            },
            {
                "employee_name": "Auth Flight Docs Test",
                "employee_email": "auth.flight.docs.test@company.com",
                "department": "Travel",
                "manager_email": "obamigbade@gmail.com",
                "company_id": "demo_company",
                "role_level": "employee",
                "active": True
            },
            {
                "employee_name": "Auth Rejection Test",
                "employee_email": "auth.rejection.test@company.com",
                "department": "Compliance",
                "manager_email": "obamigbade@gmail.com",
                "company_id": "demo_company",
                "role_level": "employee",
                "active": True
            }
        ]
        for emp in employees:
            emp_email = emp["employee_email"]
            doc_ref = target_db.collection("employees").document(emp_email)
            emp["employee_id"] = emp_email.split("@")[0]
            doc_ref.set(emp, merge=True)
        logger.info("Demo employees seeded successfully.")
    except Exception as e:
        logger.error(f"Failed to seed demo employees: {e}")

def init_firestore():
    global _real_db
    try:
        _real_db = firestore.Client(project=PROJECT_ID)
        logger.info("Successfully connected to Firestore database.")
        seed_demo_employees(_real_db)
    except Exception as e:
        logger.error(f"Error initializing Firestore: {e}")
        _real_db = None
    return _real_db

class FirestoreProxy:
    def __getattr__(self, name):
        import sys
        main_mod = sys.modules.get("submission_frontend.main")
        if main_mod and hasattr(main_mod, "db"):
            actual_db = main_mod.db
            if actual_db is not self and actual_db is not None:
                return getattr(actual_db, name)
        return getattr(_real_db, name)

    def __bool__(self):
        import sys
        main_mod = sys.modules.get("submission_frontend.main")
        if main_mod and hasattr(main_mod, "db"):
            actual_db = main_mod.db
            if actual_db is not self and actual_db is not None:
                return bool(actual_db)
        return bool(_real_db)

# Initialize real db client
_real_db = init_firestore()

# Export FirestoreProxy instance
db = FirestoreProxy()

