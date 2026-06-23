/*******************************************************************************
 * ENTERPRISE EXPENSE REPORT WORKFLOW FRONTEND UPGRADE (JS)
 ******************************************************************************/

let activeReportId = null;
let currentReportClaims = [];
let allReports = []; // For local in-memory filtering

// Initialize tab click handling for 'reports'
const originalSwitchTab = switchTab;
switchTab = function(tab) {
    if (tab === 'reports') {
        document.querySelectorAll(".tab-section").forEach(sec => sec.style.display = "none");
        document.querySelectorAll(".tab-btn").forEach(btn => {
            btn.classList.remove("active");
            btn.style.color = "var(--text-muted)";
            btn.style.borderBottom = "none";
        });

        const activeBtn = document.getElementById("tab-reports");
        if (activeBtn) {
            activeBtn.classList.add("active");
            activeBtn.style.color = "white";
        }

        document.getElementById("section-reports").style.display = "block";
        closeReportBuilder();
        fetchMyReports();
    } else {
        originalSwitchTab(tab);
    }
};

// Override fetchPendingApprovals to also include reports pending review
const originalFetchPendingApprovals = fetchPendingApprovals;
fetchPendingApprovals = async function() {
    // Run original to fetch individual claims
    await originalFetchPendingApprovals();
    
    // Also append reports pending review to the dashboard grid if the user is a manager or admin
    if (USER_ROLE === "manager" || USER_ROLE === "finance_admin") {
        try {
            const res = await fetch("/api/reports?status=pending_manager_review");
            if (!res.ok) return;
            const reports = await res.json();
            
            if (reports.length > 0) {
                const grid = document.getElementById("dashboard-grid");
                
                // If there was an empty state of querying agent registry, remove it
                const emptyState = grid.querySelector(".empty-state");
                if (emptyState && emptyState.textContent.includes("Querying Agent Registry")) {
                    grid.innerHTML = "";
                }
                
                reports.forEach(rep => {
                    // Check if report card is already rendered
                    if (document.getElementById(`report-card-pending-${rep.report_id}`)) return;
                    
                    const card = document.createElement("div");
                    card.id = `report-card-pending-${rep.report_id}`;
                    card.className = "claim-card pending";
                    card.style.position = "relative";
                    card.style.background = "linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%)";
                    card.style.border = "1px solid rgba(99, 102, 241, 0.25)";
                    card.style.borderRadius = "20px";
                    card.style.padding = "1.5rem";
                    card.style.display = "flex";
                    card.style.flexDirection = "column";
                    card.style.gap = "1rem";
                    
                    card.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span class="badge" style="background: rgba(99, 102, 241, 0.15); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3); margin-bottom: 0.5rem; display: inline-block;">EXPENSE REPORT REVIEW</span>
                                <h3 style="font-size: 1.15rem; font-weight: 700; color: white;">${escapeHtml(rep.report_title)}</h3>
                                <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.1rem;">Period: ${rep.report_period_start} to ${rep.report_period_end}</p>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 1.25rem; font-weight: 800; color: white;">${formatMoney(rep.total_claimed_amount)}</div>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">Reimbursable: ${formatMoney(rep.total_reimbursable_amount)}</span>
                            </div>
                        </div>
                        
                        <div style="background: rgba(0,0,0,0.2); border-radius: 12px; padding: 0.75rem; font-size: 0.8rem; display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
                            <div><strong style="color: var(--text-muted);">Employee:</strong> <span style="color: white;">${escapeHtml(rep.employee_name)}</span></div>
                            <div><strong style="color: var(--text-muted);">Department:</strong> <span style="color: white;">${escapeHtml(rep.department)}</span></div>
                            <div><strong style="color: var(--text-muted);">Exceptions:</strong> <span style="color: #f43f5e; font-weight: 600;">${rep.policy_exception_count}</span></div>
                            <div><strong style="color: var(--text-muted);">Claims:</strong> <span style="color: white;">${rep.claim_count}</span></div>
                        </div>

                        <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: auto; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.05);">
                            <button class="btn btn-receipt" onclick="switchTab('reports'); loadReportBuilder('${rep.report_id}')" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; font-weight: 600; border-radius: 8px; width: auto; height: auto;">
                                Open Report Dossier
                            </button>
                        </div>
                    `;
                    grid.appendChild(card);
                });
            }
        } catch (err) {
            console.error("Error appending pending reports review queue:", err);
        }
    }
};

// Fetch reports from backend
async function fetchMyReports() {
    const grid = document.getElementById("reports-grid");
    grid.innerHTML = `
        <div class="empty-state" style="grid-column: 1/-1;">
            <div class="spinner"></div>
            <h3>Loading Expense Reports...</h3>
            <p>Retrieving draft and submitted corporate expense reports from database...</p>
        </div>
    `;

    try {
        const response = await fetch("/api/reports");
        if (!response.ok) throw new Error("Failed to fetch reports");
        allReports = await response.json();
        
        // Show filter bar for managers and admins
        const filterBar = document.getElementById("reports-filter-bar");
        if (USER_ROLE === "manager" || USER_ROLE === "finance_admin") {
            filterBar.style.display = "flex";
        } else {
            filterBar.style.display = "none";
        }

        applyReportFilters();
    } catch (err) {
        console.error("Error fetching reports:", err);
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1; border-color: var(--danger-glow);">
                <h3>Failed to load reports</h3>
                <p>${err.message}</p>
            </div>
        `;
    }
}

// In-memory filters
function applyReportFilters() {
    const employeeVal = document.getElementById("filter-employee").value.trim().toLowerCase();
    const managerVal = document.getElementById("filter-manager").value.trim().toLowerCase();
    const deptVal = document.getElementById("filter-department").value;
    const statusVal = document.getElementById("filter-status").value;

    const filtered = allReports.filter(r => {
        if (employeeVal && !r.employee_name.toLowerCase().includes(employeeVal) && !r.employee_email.toLowerCase().includes(employeeVal)) return false;
        if (managerVal && !r.manager_email.toLowerCase().includes(managerVal)) return false;
        if (deptVal && r.department !== deptVal) return false;
        if (statusVal && r.status !== statusVal) return false;
        return true;
    });

    renderReportsGrid(filtered);
}

function onReportFilterChange() {
    applyReportFilters();
}

function clearReportFilters() {
    document.getElementById("filter-employee").value = "";
    document.getElementById("filter-manager").value = "";
    document.getElementById("filter-department").value = "";
    document.getElementById("filter-status").value = "";
    applyReportFilters();
}

// Render grid of cards
function renderReportsGrid(reports) {
    const grid = document.getElementById("reports-grid");
    if (!reports || reports.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <h3>No Expense Reports Found</h3>
                <p>You haven't drafted any expense report containers yet. Click "New Expense Report" to get started.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = reports.map(r => {
        const start = r.report_period_start || "N/A";
        const end = r.report_period_end || "N/A";
        const claimCount = r.claim_count || 0;
        const missingCount = r.missing_document_count || 0;
        const exceptionCount = r.policy_exception_count || 0;
        
        let statusBadge = "";
        let actionBtnText = "View Report";
        let isEditable = r.status === "draft" || r.status === "returned_to_employee";
        
        if (isEditable) {
            actionBtnText = "Edit / Build";
        } else if (r.status === "pending_manager_review") {
            actionBtnText = USER_ROLE === "employee" ? "View Details" : "Review Dossier";
        }

        switch (r.status) {
            case 'draft':
                statusBadge = `<span class="badge" style="background: rgba(255,255,255,0.05); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1);">Draft</span>`;
                break;
            case 'pending_manager_review':
                statusBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.25);">Reviewing</span>`;
                break;
            case 'returned_to_employee':
                statusBadge = `<span class="badge" style="background: rgba(244, 63, 94, 0.15); color: #fda4af; border: 1px solid rgba(244, 63, 94, 0.3);">Returned</span>`;
                break;
            case 'approved':
                statusBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.25);">Approved</span>`;
                break;
            case 'rejected':
                statusBadge = `<span class="badge" style="background: rgba(244, 63, 94, 0.1); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.25);">Rejected</span>`;
                break;
            default:
                statusBadge = `<span class="badge" style="background: rgba(255,255,255,0.05); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1);">${r.status}</span>`;
        }

        let warningBadges = "";
        if (missingCount > 0) {
            warningBadges += `<span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border-color: rgba(245,158,11,0.2); font-size: 0.72rem; margin-right: 0.3rem;"><strong style="font-weight: 700;">!</strong> ${missingCount} Missing Docs</span>`;
        }
        if (exceptionCount > 0) {
            warningBadges += `<span class="badge" style="background: rgba(244, 63, 94, 0.1); color: #f43f5e; border-color: rgba(244,63,94,0.2); font-size: 0.72rem;"><strong style="font-weight: 700;">!</strong> ${exceptionCount} Exceptions</span>`;
        }

        const dateUpdated = r.updated_at ? new Date(r.updated_at).toLocaleDateString() : "N/A";

        return `
            <div class="report-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                    ${statusBadge}
                    <span style="font-size: 0.75rem; color: var(--text-muted);">Updated: ${dateUpdated}</span>
                </div>
                <h3 class="report-title">${escapeHtml(r.report_title)}</h3>
                
                <div class="report-meta">
                    <div class="report-meta-item">
                        <span>📅</span> Period: <strong>${start}</strong> to <strong>${end}</strong>
                    </div>
                    <div class="report-meta-item">
                        <span>👤</span> Employee: <strong>${escapeHtml(r.employee_name)}</strong>
                    </div>
                    <div class="report-meta-item">
                        <span>📂</span> claims count: <strong>${claimCount} claim item(s)</strong>
                    </div>
                    ${warningBadges ? `<div style="margin-top: 0.25rem;">${warningBadges}</div>` : ''}
                </div>

                <div class="report-totals">
                    <div class="report-total-box">
                        <span class="report-total-label">Total Claimed</span>
                        <span class="report-total-val">${formatMoney(r.total_claimed_amount)}</span>
                    </div>
                    <div class="report-total-box" style="align-items: flex-end;">
                        <span class="report-total-label">Reimbursable</span>
                        <span class="report-total-val" style="color: var(--success);">${formatMoney(r.total_reimbursable_amount)}</span>
                    </div>
                </div>

                <button class="btn btn-receipt" onclick="loadReportBuilder('${r.report_id}')" style="margin-top: 1.25rem; width: 100%; border-radius: 12px; font-weight: 600; padding: 0.6rem;">
                    ${actionBtnText}
                </button>
            </div>
        `;
    }).join('');
}

// Drawer Open/Close
function openNewReportDrawer() {
    document.getElementById("drawer-new-report").classList.add("active");
    document.getElementById("slide-overlay").classList.add("active");
    
    // Auto populate default start/end dates (current month)
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    
    document.getElementById("report-start-date").value = `${y}-${m}-01`;
    // Last day of month
    const lastDay = new Date(y, now.getMonth() + 1, 0).getDate();
    document.getElementById("report-end-date").value = `${y}-${m}-${lastDay}`;
    document.getElementById("report-title-input").value = "";
    document.getElementById("report-travel-week").value = "";
    
    // Admin selector
    const adminSelector = document.getElementById("drawer-employee-selector");
    if (USER_ROLE === "finance_admin") {
        adminSelector.style.display = "block";
    } else {
        adminSelector.style.display = "none";
    }
}

function closeNewReportDrawer() {
    document.getElementById("drawer-new-report").classList.remove("active");
    document.getElementById("slide-overlay").classList.remove("active");
}

// Create new report
async function submitCreateReport() {
    const title = document.getElementById("report-title-input").value.trim();
    const start = document.getElementById("report-start-date").value;
    const end = document.getElementById("report-end-date").value;
    const travelWeek = document.getElementById("report-travel-week").value.trim();
    const emulatedEmployee = USER_ROLE === "finance_admin" ? document.getElementById("drawer-emulated-employee").value : "";

    if (!title) {
        showToast("Report title is required.", "error");
        return;
    }

    try {
        const response = await fetch("/api/reports", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                report_title: title,
                report_period_start: start,
                report_period_end: end,
                travel_week: travelWeek || null,
                employee_email: emulatedEmployee || null
            })
        });

        if (!response.ok) throw new Error("Failed to create report");
        const data = await response.json();
        
        closeNewReportDrawer();
        showToast(`Created draft report "${title}"!`, "success");
        
        // Open the builder immediately!
        loadReportBuilder(data.report_id);
    } catch (err) {
        console.error(err);
        showToast("Error creating report: " + err.message, "error");
    }
}

// Load detailed view inside report builder
async function loadReportBuilder(reportId) {
    activeReportId = reportId;
    document.getElementById("reports-dashboard-container").style.display = "none";
    document.getElementById("report-builder-container").style.display = "block";
    
    // Loading state in tables
    document.getElementById("builder-claims-tbody").innerHTML = `
        <tr>
            <td colspan="6" style="padding: 2rem; text-align: center;">
                <div class="spinner"></div>
                <p style="margin-top: 0.5rem; color: var(--text-muted);">Syncing report dossier...</p>
            </td>
        </tr>
    `;

    try {
        const response = await fetch(`/api/reports/${reportId}`);
        if (!response.ok) throw new Error("Failed to fetch report details");
        const detail = await response.json();
        
        const report = detail.report;
        currentReportClaims = detail.claims;
        const documents = detail.documents;
        const decisions = detail.decisions;
        const auditLogs = detail.audit_logs;

        // RENDER HEADER
        document.getElementById("builder-report-title").textContent = report.report_title;
        document.getElementById("builder-report-meta").innerHTML = `
            👤 Employee: <strong>${escapeHtml(report.employee_name)}</strong> (${escapeHtml(report.employee_email)}) 
            &nbsp;&bull;&nbsp; 💼 Dept: <strong>${escapeHtml(report.department)}</strong> 
            &nbsp;&bull;&nbsp; 📅 Period: <strong>${report.report_period_start}</strong> to <strong>${report.report_period_end}</strong>
        `;

        // STATS
        document.getElementById("stat-total-claimed").textContent = formatMoney(report.total_claimed_amount);
        document.getElementById("stat-total-reimbursable").textContent = formatMoney(report.total_reimbursable_amount);
        document.getElementById("stat-policy-exceptions").textContent = report.policy_exception_count;
        document.getElementById("stat-missing-documents").textContent = report.missing_document_count;

        // RETURN BANNER
        const returnBanner = document.getElementById("builder-return-reason-banner");
        if (report.status === "returned_to_employee" && report.return_reason) {
            returnBanner.style.display = "block";
            document.getElementById("builder-return-reason-text").textContent = report.return_reason;
        } else {
            returnBanner.style.display = "none";
        }

        // EDITABILITY & ROLE CHECKS
        const isEditable = report.status === "draft" || report.status === "returned_to_employee";
        const isEmployeeOwner = report.employee_email === USER_EMAIL;
        const isReviewer = USER_ROLE === "manager" || USER_ROLE === "finance_admin";
        
        // Hide add claim and upload buttons if not editable or not employee owner
        const addClaimBtn = document.getElementById("btn-add-line-item");
        const uploadContainer = document.getElementById("builder-upload-container");
        
        if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
            addClaimBtn.style.display = "inline-block";
            uploadContainer.style.display = "block";
            // Show actions columns in claims table
            document.querySelectorAll(".builder-actions-column").forEach(el => el.style.display = "table-cell");
        } else {
            addClaimBtn.style.display = "none";
            uploadContainer.style.display = "none";
            // Hide actions columns
            document.querySelectorAll(".builder-actions-column").forEach(el => el.style.display = "none");
        }

        // RENDER CLAIMS TABLE
        const tbody = document.getElementById("builder-claims-tbody");
        if (currentReportClaims.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="padding: 2.5rem; text-align: center; color: var(--text-muted);">
                        No claims in this report. Click "+ Add Expense Claim" to insert one.
                    </td>
                </tr>
            `;
        } else {
            tbody.innerHTML = currentReportClaims.map(c => {
                let complianceBadge = "";
                let receiptBadge = "";
                
                // Compliance Status
                if (c.policy_status === "approved" || c.policy_status === "auto_approved") {
                    complianceBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border-color: rgba(16,185,129,0.25);">Policy Compliant</span>`;
                } else if (c.policy_status === "warn" || c.policy_status === "warning") {
                    complianceBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border-color: rgba(245,158,11,0.25);">Warning</span>`;
                } else if (c.policy_status === "rejected" || c.policy_status === "critical") {
                    complianceBadge = `<span class="badge" style="background: rgba(244, 63, 94, 0.1); color: #f43f5e; border-color: rgba(244,63,94,0.25);">Exception</span>`;
                } else {
                    complianceBadge = `<span class="badge" style="background: rgba(255,255,255,0.05); color: #cbd5e1; border-color: rgba(255,255,255,0.1);">${c.policy_status || "Pending"}</span>`;
                }

                // Document Status
                const missing = c.missing_documents || [];
                if (missing.length === 0) {
                    receiptBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border-color: rgba(16,185,129,0.2);">Attached</span>`;
                } else {
                    receiptBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border-color: rgba(245,158,11,0.25); cursor: pointer;" title="Missing: ${missing.join(', ')}">⚠️ Missing Receipt</span>`;
                }

                let actionsHTML = "";
                if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
                    actionsHTML = `
                        <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
                            <button class="btn btn-receipt" onclick="openClaimFormModal('${c.claim_id}')" style="padding: 0.25rem 0.5rem; font-size: 0.72rem; border-radius: 6px; width: auto; height: auto;">Edit</button>
                            <button class="btn btn-receipt" onclick="deleteClaimFromReport('${c.claim_id}')" style="padding: 0.25rem 0.5rem; font-size: 0.72rem; border-radius: 6px; width: auto; height: auto; border-color: rgba(244,63,94,0.4); color: #fda4af;">Delete</button>
                        </div>
                    `;
                }

                // If reviewer/manager is looking, show approve/reject icons per claim
                if (report.status === "pending_manager_review" && isReviewer) {
                    let decState = "";
                    if (c.claim_status === "approved") {
                        decState = `<span style="color: #10b981; font-weight: 600; font-size: 0.75rem;">✔️ Approved</span>`;
                    } else if (c.claim_status === "rejected") {
                        decState = `<span style="color: #f43f5e; font-weight: 600; font-size: 0.75rem;">❌ Rejected</span>`;
                    } else {
                        decState = `
                            <div style="display: flex; gap: 0.3rem; justify-content: flex-end;">
                                <button class="btn btn-receipt" onclick="decideClaimForReview('${c.claim_id}', 'approved')" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; border-color: rgba(16,185,129,0.4); color: #34d399; width: auto; height: auto;">Approve</button>
                                <button class="btn btn-receipt" onclick="decideClaimForReview('${c.claim_id}', 'rejected')" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; border-color: rgba(244,63,94,0.4); color: #f87171; width: auto; height: auto;">Reject</button>
                            </div>
                        `;
                    }
                    actionsHTML = decState;
                    // Ensure action column header/footer display is correct
                    document.querySelectorAll(".builder-actions-column").forEach(el => el.style.display = "table-cell");
                }

                return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 0.8rem 1rem;">
                            <strong style="color: white;">${escapeHtml(c.category)}</strong>
                            <span style="display: block; font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(c.description || c.business_purpose || '')}</span>
                        </td>
                        <td style="padding: 0.8rem 1rem;">${c.expense_date}</td>
                        <td style="padding: 0.8rem 1rem; font-weight: 700; color: white;">${formatMoney(c.amount)} ${c.currency}</td>
                        <td style="padding: 0.8rem 1rem;">${complianceBadge}</td>
                        <td style="padding: 0.8rem 1rem;">${receiptBadge}</td>
                        <td style="padding: 0.8rem 1rem; text-align: right;" class="builder-actions-column">${actionsHTML}</td>
                    </tr>
                `;
            }).join('');
        }

        // RENDER REPORT DOCUMENTS
        const docsList = document.getElementById("builder-documents-list");
        if (documents.length === 0) {
            docsList.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-muted); text-align: center; padding: 1rem;">No documents or receipts uploaded yet.</div>`;
        } else {
            docsList.innerHTML = documents.map(d => {
                let statusLabel = "";
                let assignActionHTML = "";
                
                if (d.assigned_to_claim && d.claim_id !== "supporting") {
                    const matchedClaim = currentReportClaims.find(cl => cl.claim_id === d.claim_id);
                    const claimText = matchedClaim ? `${matchedClaim.category} (${formatMoney(matchedClaim.amount)})` : d.claim_id;
                    statusLabel = `<span style="color: var(--success); font-size: 0.75rem; font-weight: 500;">✔️ Assigned to: ${escapeHtml(claimText)}</span>`;
                    
                    if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
                        assignActionHTML = `<button class="btn btn-receipt" onclick="unassignDocument('${d.document_id}')" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; border-color: rgba(255,255,255,0.1); color: var(--text-muted); width: auto; height: auto;">Unassign</button>`;
                    }
                } else if (d.claim_id === "supporting") {
                    statusLabel = `<span style="color: #cbd5e1; font-size: 0.75rem; font-weight: 500;">📋 Extra Supporting Doc</span>`;
                    if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
                        assignActionHTML = `<button class="btn btn-receipt" onclick="openAssignModal('${d.document_id}', '${escapeHtml(d.file_name)}')" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; width: auto; height: auto;">Reassign</button>`;
                    }
                } else {
                    statusLabel = `<span style="color: #f59e0b; font-size: 0.75rem; font-weight: 600;">⚠️ Unassigned</span>`;
                    if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
                        assignActionHTML = `<button class="btn btn-receipt" onclick="openAssignModal('${d.document_id}', '${escapeHtml(d.file_name)}')" style="padding: 0.2rem 0.4rem; font-size: 0.7rem; width: auto; height: auto; border-color: rgba(245,158,11,0.4); color: #f59e0b;">Assign Claim</button>`;
                    }
                }

                const displayType = (d.doc_type || "receipt").replace(/_/g, ' ').toUpperCase();

                return `
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--glass-border); border-radius: 10px; padding: 0.75rem; display: flex; justify-content: space-between; align-items: center; gap: 0.5rem;">
                        <div style="flex: 1; min-width: 0;">
                            <div style="display: flex; align-items: center; gap: 0.4rem;">
                                <span style="font-size: 1.1rem;">📄</span>
                                <a href="/api/document/${reportId}/${d.doc_type || 'receipt'}?path=${encodeURIComponent(d.gcs_path)}" target="_blank" style="color: #a5b4fc; font-weight: 600; text-decoration: none; font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: inline-block;">
                                    ${escapeHtml(d.file_name)}
                                </a>
                                <span style="font-size: 0.65rem; color: var(--text-muted); background: rgba(255,255,255,0.05); padding: 0.1rem 0.3rem; border-radius: 4px;">${displayType}</span>
                            </div>
                            <div style="margin-top: 0.2rem;">${statusLabel}</div>
                        </div>
                        <div>${assignActionHTML}</div>
                    </div>
                `;
            }).join('');
        }

        // RENDER LIFECYCLE AUDIT LOG
        const auditContainer = document.getElementById("builder-audit-list");
        if (auditLogs.length === 0) {
            auditContainer.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-muted); text-align: center; padding: 1rem;">No trail yet.</div>`;
        } else {
            auditContainer.innerHTML = auditLogs.map(log => {
                const cleanMsg = log.message || "";
                const displayRole = (log.actor_role || "").replace(/_/g, ' ').toUpperCase();
                const logDate = log.created_at ? new Date(log.created_at).toLocaleString() : "N/A";
                
                return `
                    <div style="position: relative; padding-bottom: 0.5rem;">
                        <span style="display: block; font-size: 0.8rem; color: white; font-weight: 500;">${escapeHtml(cleanMsg)}</span>
                        <span style="display: block; font-size: 0.7rem; color: var(--text-muted); margin-top: 0.15rem;">
                            By: ${escapeHtml(log.actor_email)} (${displayRole}) &bull; ${logDate}
                        </span>
                    </div>
                `;
            }).join('');
        }

        // RENDER ACTIONS CONTAINER
        const actionsContainer = document.getElementById("builder-actions-container");
        if (isEditable && (isEmployeeOwner || USER_ROLE === "finance_admin")) {
            actionsContainer.innerHTML = `
                <button class="btn btn-receipt" onclick="closeReportBuilder()" style="padding: 0.6rem 1.2rem; font-weight: 600; border-radius: 10px;">Save as Draft</button>
                <button class="btn btn-primary" onclick="submitReportForReview(false)" style="padding: 0.6rem 1.5rem; font-weight: 600; border-radius: 10px;">Submit Report</button>
            `;
        } else if (report.status === "pending_manager_review" && isReviewer) {
            actionsContainer.innerHTML = `
                <button class="btn btn-receipt" onclick="openReturnModal('${reportId}')" style="padding: 0.6rem 1.2rem; font-weight: 600; border-radius: 10px; border-color: rgba(245,158,11,0.4); color: #f59e0b;">Return to Employee</button>
                <button class="btn btn-receipt" onclick="rejectReportForReview()" style="padding: 0.6rem 1.2rem; font-weight: 600; border-radius: 10px; border-color: rgba(244,63,94,0.4); color: #f87171;">Reject Report</button>
                <button class="btn btn-primary" onclick="approveReportForReview()" style="padding: 0.6rem 1.5rem; font-weight: 600; border-radius: 10px;">Approve Report</button>
            `;
        } else {
            actionsContainer.innerHTML = `
                <button class="btn btn-receipt" onclick="closeReportBuilder()" style="padding: 0.6rem 1.2rem; font-weight: 600; border-radius: 10px;">Close Dossier</button>
            `;
        }

    } catch (err) {
        console.error("Error loading report builder:", err);
        showToast("Failed to load report details: " + err.message, "error");
        closeReportBuilder();
    }
}

function closeReportBuilder() {
    activeReportId = null;
    currentReportClaims = [];
    document.getElementById("report-builder-container").style.display = "none";
    document.getElementById("reports-dashboard-container").style.display = "block";
    fetchMyReports();
}

// Modal Form handling
function openClaimFormModal(claimId = null) {
    const overlay = document.getElementById("claim-modal-overlay");
    const modal = document.getElementById("modal-claim-form");
    
    // Reset inputs
    document.getElementById("claim-id-hidden").value = claimId || "";
    document.getElementById("claim-amount").value = "";
    document.getElementById("claim-purpose").value = "";
    document.getElementById("claim-description").value = "";
    document.getElementById("claim-receipt-file").value = "";
    
    // Default values
    document.getElementById("claim-category").value = "Flight";
    document.getElementById("claim-currency").value = "USD";
    
    const today = new Date().toISOString().split('T')[0];
    document.getElementById("claim-date").value = today;

    // Reset dynamic structures
    document.getElementById("claim-hotel-fields").style.display = "none";
    document.getElementById("claim-hotel-in").value = "";
    document.getElementById("claim-hotel-out").value = "";
    document.getElementById("claim-transportation-fields").style.display = "none";
    document.getElementById("claim-trans-type").value = "";
    document.getElementById("claim-mileage-row").style.display = "none";
    document.getElementById("claim-mileage").value = "";
    document.getElementById("claim-gas-cost").value = "";
    
    document.getElementById("claim-receipt-upload-row").style.display = claimId ? "none" : "block";

    if (claimId) {
        document.getElementById("claim-modal-title").textContent = "Edit Expense Claim";
        const matched = currentReportClaims.find(c => c.claim_id === claimId);
        if (matched) {
            document.getElementById("claim-category").value = matched.category || "Flight";
            document.getElementById("claim-date").value = matched.expense_date || today;
            document.getElementById("claim-amount").value = matched.amount || "";
            document.getElementById("claim-currency").value = matched.currency || "USD";
            document.getElementById("claim-purpose").value = matched.business_purpose || "";
            document.getElementById("claim-description").value = matched.description || "";
            
            onClaimCategoryChange();
            
            if (matched.category === "Hotel") {
                document.getElementById("claim-hotel-in").value = matched.check_in_date || "";
                document.getElementById("claim-hotel-out").value = matched.check_out_date || "";
            } else if (matched.category === "Transportation" || matched.category === "Rental Car" || matched.category === "Rental Car Gas" || matched.category === "Mileage") {
                document.getElementById("claim-trans-type").value = matched.transportation_type || "";
                onClaimTransTypeChange();
                document.getElementById("claim-mileage").value = matched.mileage || "";
                document.getElementById("claim-gas-cost").value = matched.gas_cost || "";
            }
        }
    } else {
        document.getElementById("claim-modal-title").textContent = "Add Expense Claim";
    }

    overlay.classList.add("active");
    modal.style.opacity = "1";
    modal.style.pointerEvents = "all";
    modal.style.transform = "translate(-50%, -50%) scale(1)";
}

function closeClaimFormModal() {
    const overlay = document.getElementById("claim-modal-overlay");
    const modal = document.getElementById("modal-claim-form");
    
    overlay.classList.remove("active");
    modal.style.opacity = "0";
    modal.style.pointerEvents = "none";
    modal.style.transform = "translate(-50%, -50%) scale(0.9)";
}

function onClaimCategoryChange() {
    const cat = document.getElementById("claim-category").value;
    const hotelFields = document.getElementById("claim-hotel-fields");
    const transFields = document.getElementById("claim-transportation-fields");

    if (cat === "Hotel") {
        hotelFields.style.display = "grid";
        transFields.style.display = "none";
    } else if (cat === "Transportation" || cat === "Rental Car" || cat === "Rental Car Gas" || cat === "Mileage") {
        hotelFields.style.display = "none";
        transFields.style.display = "flex";
        
        // Auto select transportation type if matched
        const typeSelect = document.getElementById("claim-trans-type");
        if (cat === "Mileage") {
            typeSelect.value = "personal_vehicle";
            onClaimTransTypeChange();
        } else if (cat === "Rental Car" || cat === "Rental Car Gas") {
            typeSelect.value = "rental_car";
            onClaimTransTypeChange();
        }
    } else {
        hotelFields.style.display = "none";
        transFields.style.display = "none";
    }
}

function onClaimTransTypeChange() {
    const transType = document.getElementById("claim-trans-type").value;
    const mileageRow = document.getElementById("claim-mileage-row");
    
    if (transType === "personal_vehicle") {
        mileageRow.style.display = "grid";
    } else {
        mileageRow.style.display = "none";
    }
}

// Submit single claim item
async function submitClaimForm() {
    const claimId = document.getElementById("claim-id-hidden").value;
    const category = document.getElementById("claim-category").value;
    const date = document.getElementById("claim-date").value;
    const amount = parseFloat(document.getElementById("claim-amount").value);
    const currency = document.getElementById("claim-currency").value;
    const purpose = document.getElementById("claim-purpose").value.trim();
    const desc = document.getElementById("claim-description").value.trim();

    if (isNaN(amount) || amount <= 0) {
        showToast("Claim amount must be greater than 0.", "error");
        return;
    }

    const claim_data = {
        category,
        expense_date: date,
        amount,
        currency,
        business_purpose: purpose,
        description: desc
    };

    if (category === "Hotel") {
        claim_data.check_in_date = document.getElementById("claim-hotel-in").value;
        claim_data.check_out_date = document.getElementById("claim-hotel-out").value;
    } else if (category === "Transportation" || category === "Rental Car" || category === "Rental Car Gas" || category === "Mileage") {
        const transType = document.getElementById("claim-trans-type").value;
        claim_data.transportation_type = transType;
        if (transType === "personal_vehicle") {
            claim_data.mileage = parseFloat(document.getElementById("claim-mileage").value) || 0;
            claim_data.gas_cost = parseFloat(document.getElementById("claim-gas-cost").value) || 0;
        }
    }

    try {
        const isEditing = !!claimId;
        const apiPath = isEditing 
            ? `/api/reports/${activeReportId}/claims/${claimId}` 
            : `/api/reports/${activeReportId}/claims`;
            
        const method = isEditing ? "PATCH" : "POST";

        const response = await fetch(apiPath, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(claim_data)
        });

        if (!response.ok) throw new Error("Failed to save claim line item");
        const claimResult = await response.json();

        // Handle receipt file upload if selected and not editing
        const fileInput = document.getElementById("claim-receipt-file");
        if (!isEditing && fileInput.files && fileInput.files.length > 0) {
            const formData = new FormData();
            formData.append("files", fileInput.files[0]);
            
            const uploadRes = await fetch(`/api/reports/${activeReportId}/documents`, {
                method: "POST",
                body: formData
            });
            
            if (uploadRes.ok) {
                const uploadedDocs = await uploadRes.json();
                if (uploadedDocs.length > 0) {
                    const docId = uploadedDocs[0].document_id;
                    // Auto assign to this newly created claim!
                    await fetch(`/api/reports/${activeReportId}/documents/${docId}/assign`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            claim_id: claimResult.claim_id,
                            doc_type: "receipt"
                        })
                    });
                }
            }
        }

        closeClaimFormModal();
        showToast(isEditing ? "Claim updated successfully." : "Claim item added to report!", "success");
        loadReportBuilder(activeReportId);
    } catch (err) {
        console.error(err);
        showToast("Failed to save claim: " + err.message, "error");
    }
}

// Delete Claim from report
async function deleteClaimFromReport(claimId) {
    if (!confirm("Are you sure you want to delete this expense claim line item? Any associated documents will be unassigned.")) return;
    
    try {
        const response = await fetch(`/api/reports/${activeReportId}/claims/${claimId}`, {
            method: "DELETE"
        });
        
        if (!response.ok) throw new Error("Failed to delete claim");
        showToast("Claim item deleted.", "success");
        loadReportBuilder(activeReportId);
    } catch (err) {
        console.error(err);
        showToast("Error deleting claim: " + err.message, "error");
    }
}

// Bulk Upload receipts
function triggerBulkFileInput() {
    document.getElementById("bulk-receipt-file-input").click();
}

async function handleBulkReceiptsSelect(files) {
    if (!files || files.length === 0) return;
    
    const zone = document.getElementById("bulk-receipt-dropzone");
    const originalZoneHTML = zone.innerHTML;
    zone.innerHTML = `
        <div class="spinner" style="margin: 0 auto 0.5rem auto;"></div>
        <span style="font-weight: 600;">Uploading ${files.length} document(s)...</span>
    `;
    zone.style.pointerEvents = "none";

    try {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }

        const response = await fetch(`/api/reports/${activeReportId}/documents`, {
            method: "POST",
            body: formData
        });

        if (!response.ok) throw new Error("Upload failed");
        
        showToast(`Successfully uploaded ${files.length} receipt(s)!`, "success");
    } catch (err) {
        console.error(err);
        showToast("Bulk upload failed: " + err.message, "error");
    } finally {
        zone.innerHTML = originalZoneHTML;
        zone.style.pointerEvents = "all";
        loadReportBuilder(activeReportId);
    }
}

// Assign Receipt Modal
function openAssignModal(docId, filename) {
    document.getElementById("assign-doc-id").value = docId;
    document.getElementById("assign-doc-filename").textContent = filename;
    
    const select = document.getElementById("assign-claim-select");
    
    // Populate select with claims
    let options = `<option value="">-- Supporting Document (Do Not Assign to Specific Claim) --</option>`;
    options += currentReportClaims.map(c => `
        <option value="${c.claim_id}">${escapeHtml(c.category)} - ${formatMoney(c.amount)} (${c.expense_date})</option>
    `).join('');
    
    select.innerHTML = options;
    
    // Reset classification dropdown to 'receipt'
    document.getElementById("assign-doc-type").value = "receipt";

    const overlay = document.getElementById("assign-modal-overlay");
    const modal = document.getElementById("modal-assign-receipt");
    overlay.classList.add("active");
    modal.style.opacity = "1";
    modal.style.pointerEvents = "all";
    modal.style.transform = "translate(-50%, -50%) scale(1)";
}

function closeAssignModal() {
    const overlay = document.getElementById("assign-modal-overlay");
    const modal = document.getElementById("modal-assign-receipt");
    overlay.classList.remove("active");
    modal.style.opacity = "0";
    modal.style.pointerEvents = "none";
    modal.style.transform = "translate(-50%, -50%) scale(0.9)";
}

async function submitAssignReceipt() {
    const docId = document.getElementById("assign-doc-id").value;
    const claimId = document.getElementById("assign-claim-select").value;
    const docType = document.getElementById("assign-doc-type").value;

    try {
        const response = await fetch(`/api/reports/${activeReportId}/documents/${docId}/assign`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                claim_id: claimId || null,
                doc_type: docType
            })
        });

        if (!response.ok) throw new Error("Assignment failed");
        
        closeAssignModal();
        showToast("Document assigned successfully.", "success");
        loadReportBuilder(activeReportId);
    } catch (err) {
        console.error(err);
        showToast("Error assigning document: " + err.message, "error");
    }
}

// Unassign active document
async function unassignDocument(docId) {
    try {
        const response = await fetch(`/api/reports/${activeReportId}/documents/${docId}/assign`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                claim_id: null,
                doc_type: "receipt"
            })
        });

        if (!response.ok) throw new Error("Unassignment failed");
        showToast("Document unassigned.", "success");
        loadReportBuilder(activeReportId);
    } catch (err) {
        console.error(err);
        showToast("Error: " + err.message, "error");
    }
}

// Submit Report
async function submitReportForReview(override = false) {
    if (!confirm("Are you sure you are ready to submit this full expense report for manager review?")) return;
    
    try {
        const response = await fetch(`/api/reports/${activeReportId}/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                override_missing_docs: override
            })
        });

        if (response.status === 400) {
            const errData = await response.json();
            if (errData.detail && errData.detail.includes("required document") && USER_ROLE === "finance_admin") {
                // If admin, offer override option
                if (confirm(`${errData.detail}\n\nAs Finance Admin, would you like to override this missing document blocking and force submit?`)) {
                    await submitReportForReview(true);
                    return;
                }
            } else {
                throw new Error(errData.detail || "Submission blocked.");
            }
            return;
        }

        if (!response.ok) throw new Error("HTTP Error: " + response.status);
        
        showToast("Report submitted successfully for manager review!", "success");
        closeReportBuilder();
    } catch (err) {
        console.error(err);
        showToast("Submission failed: " + err.message, "error");
    }
}

// Reviewer/Manager Actions
function openReturnModal(reportId) {
    document.getElementById("return-report-id").value = reportId;
    document.getElementById("return-reason-input").value = "";

    const overlay = document.getElementById("return-modal-overlay");
    const modal = document.getElementById("modal-return-comments");
    overlay.classList.add("active");
    modal.style.opacity = "1";
    modal.style.pointerEvents = "all";
    modal.style.transform = "translate(-50%, -50%) scale(1)";
}

function closeReturnModal() {
    const overlay = document.getElementById("return-modal-overlay");
    const modal = document.getElementById("modal-return-comments");
    overlay.classList.remove("active");
    modal.style.opacity = "0";
    modal.style.pointerEvents = "none";
    modal.style.transform = "translate(-50%, -50%) scale(0.9)";
}

async function submitReturnReport() {
    const reportId = document.getElementById("return-report-id").value;
    const reason = document.getElementById("return-reason-input").value.trim();

    if (!reason) {
        showToast("Please provide a return reason comment.", "error");
        return;
    }

    try {
        const response = await fetch(`/api/reports/${reportId}/return`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reason })
        });

        if (!response.ok) throw new Error("Return execution failed");
        
        closeReturnModal();
        showToast("Report returned to employee for revisions.", "success");
        closeReportBuilder();
    } catch (err) {
        console.error(err);
        showToast("Error: " + err.message, "error");
    }
}

async function rejectReportForReview() {
    const reason = prompt("Please enter rejection reason/justification:") || "Declined by manager.";
    if (!reason) return;

    try {
        const response = await fetch(`/api/reports/${activeReportId}/reject`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reason })
        });

        if (!response.ok) throw new Error("Rejection failed");
        
        showToast("Expense report rejected.", "success");
        closeReportBuilder();
    } catch (err) {
        console.error(err);
        showToast("Error: " + err.message, "error");
    }
}

async function approveReportForReview() {
    if (!confirm("Are you sure you want to approve this entire expense report? All non-rejected claims will be marked as approved.")) return;
    
    try {
        const response = await fetch(`/api/reports/${activeReportId}/approve`, {
            method: "POST"
        });

        if (!response.ok) throw new Error("Approval failed");
        
        showToast("Expense report approved!", "success");
        closeReportBuilder();
    } catch (err) {
        console.error(err);
        showToast("Error: " + err.message, "error");
    }
}

async function decideClaimForReview(claimId, decision) {
    const reason = decision === 'rejected' ? (prompt("Please enter a reason for rejecting this claim line item:") || "Rejected") : "Approved by manager.";
    if (decision === 'rejected' && !reason) return;

    try {
        const response = await fetch(`/api/reports/${activeReportId}/claims/${claimId}/decision`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                decision,
                reason
            })
        });

        if (!response.ok) throw new Error("Decision failed");
        showToast(`Line item claim has been ${decision}!`, "success");
        loadReportBuilder(activeReportId);
    } catch (err) {
        console.error(err);
        showToast("Error saving claim decision: " + err.message, "error");
    }
}
