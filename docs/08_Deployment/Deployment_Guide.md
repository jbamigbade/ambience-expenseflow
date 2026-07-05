# Ambience ExpenseFlow
# Deployment Guide

## Document Information

| Field | Value |
|---|---|
| Document ID | AEF-DEP-001 |
| Document Title | Deployment Guide |
| Product | Ambience ExpenseFlow |
| Version | 1.0 |
| Status | Draft |
| Classification | Confidential – Internal |
| Owner | DevOps / Cloud Engineering |
| Author | John Bamigbade |
| Created | July 2026 |
| Review Frequency | Quarterly |
| Related Documents | Cloud Architecture, Infrastructure Architecture, CI/CD, Production Checklist |

---

## 1. Executive Summary

This guide defines the deployment process for Ambience ExpenseFlow from local development through production release. The platform is designed for Google Cloud deployment using FastAPI, Cloud Run, Firestore, Cloud Storage, Vertex AI, Pub/Sub, and Google Cloud monitoring services.

---

## 2. Deployment Objectives

The deployment process must ensure:

- Reliable releases
- Repeatable deployment steps
- Minimal downtime
- Secure configuration
- Environment separation
- Rollback capability
- Monitoring visibility
- Production readiness

---

## 3. Target Deployment Environments

Recommended environments:

```text
Local
Development
Staging
Production

Each environment should have separate:

Environment variables
Secrets
Firestore resources
Cloud Storage buckets
Service accounts
Logging and monitoring


User Browser
    ↓
HTTPS
    ↓
Cloud Run
    ↓
FastAPI Application
    ↓
Firestore
    ↓
Cloud Storage
    ↓
Vertex AI
    ↓
Cloud Logging / Monitoring

5. Prerequisites

Before deployment, verify:

Google Cloud project exists
Billing enabled
Cloud Run enabled
Firestore enabled
Cloud Storage enabled
Vertex AI enabled
Pub/Sub enabled
Artifact Registry enabled
Required IAM roles configured
Environment variables prepared
Secrets stored securely


6. Local Deployment

PowerShell:

cd "D:\02_AI_and_Data\Kaggle-AI-Agents\Capstone"
uv run pytest
uv run uvicorn submission_frontend.main:app --reload --host 127.0.0.1 --port 8000

Local URL:

http://127.0.0.1:8000

7. Build Process

Recommended build steps:

uv run pytest
docker build -t ambience-expenseflow .

The build must pass:

Unit tests
Integration tests
Security checks
Lint checks
Dependency validation

8. Google Cloud Run Deployment

Example deployment command:

gcloud run deploy ambience-expenseflow `
  --source . `
  --region us-west1 `
  --allow-unauthenticated

Production deployments should use authenticated access and secure identity controls.

9. Environment Variables

Required variables may include:

AUTH_ENABLED
GOOGLE_CLOUD_PROJECT
GCP_REGION
FIRESTORE_DATABASE
GCS_BUCKET_NAME
VERTEX_AI_LOCATION
SESSION_SECRET
ENVIRONMENT

Secrets should not be stored in source control.

Use:

Google Secret Manager

10. Deployment Validation

After deployment verify:

Application loads
Login works
Dashboard loads
Expense submission works
Manager approvals work
Firestore connection works
Cloud Storage upload works
Vertex AI service responds
Audit logs are generated
Export functions work
11. Smoke Test

Run after every deployment:

Login
Create expense report
Add line item
Upload receipt
Submit report
Approve report
View audit trail
Export CSV
Logout
12. Rollback Procedure

Rollback is required when:

Application fails to start
Critical workflows fail
Security issue discovered
Data corruption risk detected

Rollback steps:

Identify last stable revision.
Route traffic back to stable revision.
Verify application health.
Notify stakeholders.
Open incident review.

Cloud Run supports revision rollback through the Google Cloud Console or CLI.

13. Monitoring

Monitor:

Cloud Run health
API latency
Error rate
Firestore read/write latency
Cloud Storage failures
Vertex AI failures
Authentication failures
Export failures
14. Logging

Log categories:

Application logs
Security logs
Audit logs
Deployment logs
AI logs
Integration logs

Logs should be centralized in Google Cloud Logging.

15. Production Release Approval

Production deployment requires approval from:

Product Owner
Engineering Lead
QA Lead
Security Reviewer
Deployment Owner

16. Post-Deployment Checklist

 Application reachable
 Login verified
 Dashboard verified
 Expense submission verified
 Approval verified
 Audit trail verified
 Exports verified
 Monitoring healthy
 Logs reviewed
 Stakeholders notified

17. Future Enhancements

GitHub Actions deployment
Cloud Build pipeline
Terraform infrastructure
Blue/green deployments
Canary deployments
Automated rollback
Synthetic monitoring
Multi-region deployment

18. Conclusion

This Deployment Guide provides a repeatable and secure process for deploying Ambience ExpenseFlow across environments. By following structured validation, monitoring, rollback, and approval procedures, the platform can be operated as a reliable enterprise SaaS solution.

| Version | Date      | Author         | Description              |
| ------- | --------- | -------------- | ------------------------ |
| 1.0     | July 2026 | John Bamigbade | Initial deployment guide |

© 2026 Ambience ExpenseFlow
Confidential – Internal Use Only.
