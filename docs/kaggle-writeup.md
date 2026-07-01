**# Ambience ExpenseFlow: Enterprise AI Agent for Travel \& Expense Compliance**



**## Subtitle**



**A secure multi-agent enterprise platform that automates travel and expense reporting, compliance validation, manager approvals, supporting documentation, and audit timelines using Google ADK, Cloud Run, Firestore, Pub/Sub, and enterprise-grade security controls.**



**\*\*Track:\*\* Agents for Business**



**---**



**# Problem Statement**



**Enterprise travel and expense management remains highly manual, fragmented, and difficult to audit. Employees often submit expenses through disconnected systems, managers manually review claims, finance teams struggle to enforce policies consistently, and auditors spend significant time reconstructing historical events.**



**These inefficiencies create several business risks:**



**\* Delayed reimbursement cycles**

**\* Policy violations**

**\* Missing receipts and documentation**

**\* Inconsistent manager approvals**

**\* Limited audit traceability**

**\* Increased operational costs**

**\* Reduced employee productivity**



**Organizations need an intelligent system capable of coordinating multiple stakeholders while maintaining compliance, transparency, and security.**



**Ambience ExpenseFlow was built to solve this problem.**



**---**



**# Solution Overview**



**Ambience ExpenseFlow is an enterprise AI-powered travel and expense management platform that orchestrates the complete expense lifecycle from submission to approval and historical audit tracking.**



**The platform combines AI agents, business rules, security controls, and human approvals into a single unified system.**



**The application supports multiple personas:**



**### Employee**



**\* Submit expenses**

**\* Upload supporting documents**

**\* View personal reports**

**\* Track claim status**



**### Manager**



**\* Review expense submissions**

**\* Approve or reject requests**

**\* Validate policy exceptions**

**\* Monitor assigned reports**



**### Finance Administrator**



**\* Oversee enterprise operations**

**\* Monitor historical records**

**\* Review audit timelines**

**\* Track compliance metrics**



**---**



**# Why AI Agents?**



**Traditional expense systems rely heavily on manual intervention.**



**AI agents uniquely improve this process because they can:**



**\* Analyze policies in real time**

**\* Validate supporting documents**

**\* Route claims intelligently**

**\* Coordinate multiple workflows**

**\* Create immutable audit histories**

**\* Reduce human review workload**



**Rather than replacing human decision makers, Ambience ExpenseFlow introduces Human-in-the-Loop (HITL) collaboration.**



**High-risk decisions remain under human control.**



**---**



**# Architecture**



**The platform was built using an event-driven architecture.**



**Core technologies include:**



**## Backend**



**\* Python**

**\* Google ADK**

**\* FastAPI**



**## Data Layer**



**\* Firestore**

**\* Pub/Sub**



**## Infrastructure**



**\* Google Cloud Run**

**\* Terraform**



**## Frontend**



**\* Python-based enterprise dashboard**



**## Authentication**



**\* Google OIDC Sign-In**



**## Testing**



**\* Pytest**

**\* ADK evaluation framework**



**---**



**# Multi-Agent System Design**



**The system coordinates multiple specialized agents.**



**## Expense Validation Agent**



**Responsibilities:**



**\* Analyze expense submissions**

**\* Validate categories**

**\* Detect policy violations**

**\* Identify reimbursement eligibility**



**## Policy Compliance Agent**



**Responsibilities:**



**\* Compare expenses against rules**

**\* Flag exceptions**

**\* Detect missing documentation**

**\* Generate compliance summaries**



**## Per Diem Agent**



**Responsibilities:**



**\* Calculate travel allowances**

**\* Validate limits**

**\* Determine reimbursable amounts**



**## Approval Routing Agent**



**Responsibilities:**



**\* Route reports to managers**

**\* Trigger human approvals**

**\* Escalate high-risk claims**



**## Audit Agent**



**Responsibilities:**



**\* Create immutable timelines**

**\* Record state transitions**

**\* Preserve historical records**



**---**



**# Features Demonstrated**



**The application includes multiple enterprise features.**



**## Login Page**



**Users authenticate securely using Google OIDC.**



**The system identifies user roles and grants appropriate access.**



**## My Reports**



**Employees can view all submitted reports.**



**## Submit Expense**



**Employees enter:**



**\* Expense category**

**\* Amount**

**\* Currency**

**\* Date**

**\* Business purpose**

**\* Description**



**The compliance engine immediately evaluates submissions.**



**## Supporting Documents**



**Users can upload:**



**\* Receipts**

**\* Flight tickets**

**\* Hotel receipts**

**\* Manager approval letters**

**\* Mileage logs**

**\* Parking receipts**



**## Pending Approvals**



**Managers review assigned claims.**



**## Expense History**



**Finance administrators access historical records.**



**## Audit Timeline**



**Every action is permanently recorded.**



**---**



**# Key Concepts Demonstrated**



**This project intentionally demonstrates concepts learned during Kaggle's 5-Day AI Agents Intensive.**



**## 1. Agent System (ADK)**



**Google ADK coordinates multiple agents.**



**## 2. MCP Integration**



**Model Context Protocol principles were used to standardize interactions between reasoning systems and external resources.**



**## 3. Antigravity Workflow**



**Development followed agentic workflows taught during the course.**



**## 4. Security Features**



**Multiple security layers were implemented.**



**## 5. Deployability**



**The application was deployed to Google Cloud Run.**



**## 6. Agent Skills**



**Custom skills automate validation and routing.**



**## 7. Evaluation**



**Automated tests validate system quality.**



**---**



**# Security Implementation**



**Security was a primary design goal.**



**The platform implements:**



**## Authentication**



**Google OIDC Sign-In**



**## Authorization**



**Role-based access control**



**## Human-in-the-Loop**



**Managers approve high-risk actions.**



**## Validation**



**Claims are verified before approval.**



**## Audit Logging**



**All actions are recorded.**



**## Defensive Defaults**



**Policy-first behavior prevents unsafe actions.**



**---**



**# Evaluation Framework**



**The system includes a comprehensive testing strategy.**



**Three levels of testing were implemented.**



**## Unit Tests**



**Examples:**



**\* Dashboard authentication**

**\* Review decisions**

**\* Route expense workflows**



**## Integration Tests**



**Examples:**



**\* Agent communication**

**\* Runtime behavior**

**\* End-to-end server tests**



**## Evaluation Tests**



**Synthetic datasets validate AI reasoning.**



**This framework ensures reliability and repeatability.**



**---**



**# Deployment**



**The platform is fully deployable.**



**Deployment stack:**



**\* Google Cloud Run**

**\* Terraform**

**\* Firestore**

**\* Pub/Sub**



**The application is publicly accessible.**



**Users can:**



**\* Log in**

**\* Submit expenses**

**\* Upload documents**

**\* Review reports**

**\* Monitor audit trails**



**without requiring local installation.**



**---**



**# Business Impact**



**Ambience ExpenseFlow delivers measurable benefits.**



**## Reduced Manual Work**



**AI automates repetitive reviews.**



**## Improved Compliance**



**Policies are consistently enforced.**



**## Faster Reimbursements**



**Employees receive quicker decisions.**



**## Better Transparency**



**Stakeholders see complete workflows.**



**## Stronger Audit Readiness**



**Historical records remain accessible.**



**## Lower Operational Costs**



**Manual effort is reduced.**



**---**



**# Challenges Encountered**



**Several challenges were addressed.**



**## Multi-role Coordination**



**Different users required different experiences.**



**## State Synchronization**



**Audit histories needed consistency.**



**## Human Oversight**



**Automation had to remain safe.**



**## User Experience**



**Complex workflows needed a simple interface.**



**These challenges were solved using event-driven architecture.**



**---**



**# Lessons Learned**



**This project demonstrated that enterprise AI systems are not simply chatbots.**



**Successful AI agents require:**



**\* Strong architecture**

**\* Security controls**

**\* Human oversight**

**\* Evaluation frameworks**

**\* Reliable infrastructure**



**The course highlighted that agentic systems succeed when reasoning and execution are combined responsibly.**



**---**



**# Future Enhancements**



**Potential future improvements include:**



**\* ERP integrations**

**\* SAP integrations**

**\* Oracle integrations**

**\* Automated fraud detection**

**\* Predictive analytics**

**\* International policy support**

**\* Multi-currency optimization**



**The current system already functions as a complete enterprise solution.**



**---**



**# Project Resources**



**## Public GitHub Repository**



[**https://github.com/jbamigbade/ambience-expenseflow**](https://github.com/jbamigbade/ambience-expenseflow)



**## Live Application**



**Google Cloud Run deployment.**



**## Screenshots Included**



**1. Login Page**

**2. My Reports**

**3. Submit Expense**

**4. Supporting Documents**

**5. Pending Approvals**

**6. Employee Portal**

**7. Legacy CLI**

**8. Report Workflow**

**9. Expense History**

**10. Audit Timeline**

**11. Sample Submission Report**



**---**

**# Acknowledgement – Soli Deo Gloria**



**> “Now to the King eternal, immortal, invisible, the only God, be honor and glory for ever and ever. Amen.” — 1 Timothy 1:17**



**\*\*Soli Deo Gloria (Glory to God Alone).\*\***



**I give all glory, honor, thanksgiving, and praise to \*\*God the Father, God the Son (Jesus Christ), and God the Holy Spirit\*\* for the wisdom, grace, strength, perseverance, and opportunity to complete this project.**



**This capstone represents not only the application of modern AI agent technologies, but also a commitment to excellence, integrity, stewardship, and service to others.**



**I am grateful for the opportunity provided through \*\*Kaggle's 5-Day AI Agents: Intensive Vibe Coding Course with Google\*\*, which enabled the transformation of theoretical concepts into a practical, enterprise-grade solution.**



**May this work serve as an instrument that helps organizations operate more efficiently, ethically, and transparently while demonstrating how AI can be developed responsibly to benefit people and businesses.**



**\*\*Soli Deo Gloria — Glory to God Alone.\*\***



