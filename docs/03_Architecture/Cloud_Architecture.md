# Ambience ExpenseFlow
# Cloud Architecture

## Document Information

| Field                       | Value                      |
|-----------------------------|----------------------------|
| Document ID                 | AEF-ARCH-002               |
| Document Title              | Cloud Architecture         |
| Product                     | Ambience ExpenseFlow       |
| Version                     | 1.0                        |
| Status                      | Draft                      |
| Classification              | Confidential – Internal    |
| Owner                       | Cloud Engineering          |
| Author                      | John Bamigbade             |
| Created                     | July 2026                  |
| Review Frequency            | Quarterly                  |

---

## 1. Executive Summary

Ambience ExpenseFlow is designed as a cloud-native SaaS platform using Google Cloud services for application hosting, database storage, AI services, document storage, monitoring, and future production deployment.

The cloud architecture must support secure authentication, scalable application workloads, audit logging, AI-assisted compliance, document uploads, reporting exports, and future enterprise integrations.

---

## 2. Cloud Architecture Goals

The cloud platform must support:

- Secure application hosting
- Scalable API services
- Firestore data persistence
- Cloud Storage for receipts and documents
- Vertex AI integration
- Logging and monitoring
- CI/CD deployment
- Environment separation
- Backup and disaster recovery
- Future multi-tenant SaaS scaling

---

## 3. Current Cloud Services

Current and planned Google Cloud components include:

- Cloud Run
- Firestore
- Cloud Storage
- Vertex AI
- Cloud Logging
- Cloud Monitoring
- IAM
- Secret Manager
- Cloud Build
- Artifact Registry

---

## 4. Target Production Architecture

```text
User Browser
    ↓
HTTPS Load Balancer
    ↓
Cloud Run Service
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

5. Application Hosting

Target hosting:

Google Cloud Run
Containerized FastAPI application
Autoscaling enabled
HTTPS only
Environment variables managed securely
Health checks enabled
6. Data Storage

Primary database:

Firestore

Stores:

organizations
users
expense reports
expense line items
approvals
audit logs
policies
reimbursement records
corporate card transactions
7. Object Storage

Cloud Storage will store:

receipt images
PDF receipts
exported CSV files
exported Excel files
generated reports
audit evidence packages

Storage requirements:

access-controlled
encrypted
tenant-aware
retention-managed

8. AI Services

Vertex AI supports:

policy evaluation
receipt intelligence roadmap
natural language query roadmap
risk scoring roadmap
AI assistant roadmap

AI calls must be:

non-blocking where possible
timeout protected
logged
auditable
fallback-safe

9. Identity and Access Management

IAM principles:

least privilege
service account separation
no shared credentials
environment-specific permissions
secure key management

Future support:

Google OIDC
Microsoft Entra ID
SSO
SCIM provisioning

10. Secrets Management

Secrets should be stored in:

Google Secret Manager

Examples:

OAuth client secret
API keys
service credentials
signing keys

Secrets must not be committed to Git.

11. Environment Strategy

Recommended environments:

local
development
staging
production

Each environment should have:

separate configuration
separate secrets
separate service accounts
separate monitoring
separate deployment controls


12. Monitoring and Logging

Cloud Monitoring and Logging should track:

API latency
errors
authentication failures
failed exports
failed AI calls
database errors
security events
background job failures

13. Backup and Recovery

Backup strategy should include:

Firestore export backups
Cloud Storage lifecycle rules
audit log retention
configuration backup
disaster recovery testing

14. Scalability

Cloud architecture must support:

more users
more organizations
more reports
larger exports
more AI requests
future integrations
background job processing

15. Security Controls

Cloud security includes:

HTTPS enforcement
IAM least privilege
Secret Manager
audit logs
encrypted storage
restricted service accounts
environment isolation
future WAF / Cloud Armor

16. Future Enhancements

Planned cloud enhancements:

Pub/Sub background jobs
Cloud Tasks for async workflows
BigQuery analytics warehouse
Dataflow ETL
Cloud Armor
multi-region backup
private networking
Terraform infrastructure-as-code

17. Conclusion

The Ambience ExpenseFlow cloud architecture provides a scalable and secure foundation for the platform’s transition from demo to commercial SaaS. Google Cloud services support the application’s current capabilities while enabling future growth into enterprise-grade deployment, analytics, integrations, and AI-powered automation.