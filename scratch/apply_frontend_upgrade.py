import os
import re

print("Starting frontend upgrade script...")

with open("submission_frontend/main.py", "r", encoding="utf-8") as f:
    main_content = f.read()

# 1. Load JS from scratch/reports_upgrade.js
with open("scratch/reports_upgrade.js", "r", encoding="utf-8") as f:
    js_code = f.read()

# 2. Define CSS code to inject
css_code = """
        /* New premium styles for Expense Reports */
        .reports-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-top: 1rem;
        }
        .report-card {
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 1.5rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
            transition: var(--transition);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
        }
        .report-card:hover {
            transform: translateY(-5px);
            border-color: rgba(99, 102, 241, 0.3);
            box-shadow: 0 12px 40px 0 rgba(99, 102, 241, 0.15);
        }
        .report-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--accent));
        }
        .report-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: white;
            margin-bottom: 0.5rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .report-meta {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 1rem;
        }
        .report-meta-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .report-totals {
            display: flex;
            justify-content: space-between;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 1rem;
            margin-top: auto;
        }
        .report-total-box {
            display: flex;
            flex-direction: column;
        }
        .report-total-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .report-total-val {
            font-size: 1.1rem;
            font-weight: 700;
            color: white;
        }
        /* Slider Panel (slide drawer) */
        .slider-panel {
            position: fixed;
            top: 0;
            right: -450px;
            width: 450px;
            height: 100vh;
            background: rgba(10, 11, 26, 0.95);
            backdrop-filter: blur(20px);
            border-left: 1px solid var(--glass-border);
            box-shadow: -10px 0 40px rgba(0,0,0,0.5);
            z-index: 100;
            transition: right 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            padding: 2.5rem;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }
        .slider-panel.active {
            right: 0;
        }
        .slider-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            padding-bottom: 1rem;
        }
        /* Dropzone styling */
        .dropzone {
            border: 2px dashed rgba(99, 102, 241, 0.3);
            background: rgba(99, 102, 241, 0.02);
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            cursor: pointer;
            transition: var(--transition);
            margin: 1.5rem 0;
        }
        .dropzone:hover {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.05);
        }
        /* Unassigned docs list */
        .unassigned-docs-bar {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1.25rem;
            margin-top: 1.5rem;
        }
        .unassigned-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.25);
            color: #f59e0b;
            padding: 0.4rem 0.8rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
        }
        .unassigned-badge:hover {
            background: rgba(245, 158, 11, 0.15);
            transform: scale(1.03);
        }
"""

# 3. Define HTML section-reports to inject
html_reports_section = """
        <!-- 0. Expense Reports Section -->
        <div id="section-reports" class="tab-section" style="display: none;">
            <!-- Main reports dashboard container -->
            <div id="reports-dashboard-container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                    <div>
                        <h1 id="reports-page-title" style="font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Expense Reports</h1>
                        <p style="color: var(--text-muted); font-size: 0.95rem; margin-top: 0.2rem;">Draft, review, and manage multi-item expense report containers.</p>
                    </div>
                    <div style="display: flex; gap: 1rem;">
                        <button class="btn btn-primary" id="btn-create-report" onclick="openNewReportDrawer()" style="padding: 0.75rem 1.5rem; font-weight: 600; border-radius: 12px; display: inline-flex; align-items: center; gap: 0.5rem;">
                            <span>+</span> New Expense Report
                        </button>
                    </div>
                </div>

                <!-- Admin & Manager Filter Bar (hidden for employees) -->
                <div id="reports-filter-bar" style="background: var(--glass-bg); backdrop-filter: blur(12px); border: 1px solid var(--glass-border); border-radius: 16px; padding: 1.25rem; margin-bottom: 1.5rem; display: none; gap: 1rem; flex-wrap: wrap; align-items: center;">
                    <div style="flex: 1; min-width: 150px;">
                        <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Employee</label>
                        <input type="text" id="filter-employee" placeholder="Search email or name..." oninput="onReportFilterChange()" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.5rem; color: white; font-family: inherit;">
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Manager</label>
                        <input type="text" id="filter-manager" placeholder="Filter manager..." oninput="onReportFilterChange()" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.5rem; color: white; font-family: inherit;">
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Department</label>
                        <select id="filter-department" onchange="onReportFilterChange()" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.5rem; color: white; font-family: inherit;">
                            <option value="">All Departments</option>
                            <option value="Engineering">Engineering</option>
                            <option value="Sales">Sales</option>
                            <option value="Marketing">Sales & Marketing</option>
                            <option value="Operations">Operations</option>
                            <option value="Finance">Finance</option>
                        </select>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Status</label>
                        <select id="filter-status" onchange="onReportFilterChange()" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.5rem; color: white; font-family: inherit;">
                            <option value="">All Statuses</option>
                            <option value="draft">Draft</option>
                            <option value="pending_manager_review">Pending Manager Review</option>
                            <option value="returned_to_employee">Returned to Employee</option>
                            <option value="approved">Approved</option>
                            <option value="rejected">Rejected</option>
                        </select>
                    </div>
                    <button class="btn btn-receipt" onclick="clearReportFilters()" style="margin-top: 1.2rem; padding: 0.5rem 1rem; font-size: 0.8rem; font-weight: 600;">Clear</button>
                </div>

                <!-- Reports Grid Container -->
                <div class="reports-grid" id="reports-grid">
                    <!-- Cards will be populated dynamically -->
                </div>
            </div>

            <!-- Report Builder Detailed View (Hidden by default, shown when builder active) -->
            <div id="report-builder-container" style="display: none;">
                <!-- Header with Back button -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <button class="btn btn-receipt" onclick="closeReportBuilder()" style="padding: 0.5rem 1rem; font-size: 0.85rem; border-radius: 8px; display: inline-flex; align-items: center; gap: 0.5rem;">
                            <span>&larr;</span> Back to list
                        </button>
                        <div>
                            <h2 id="builder-report-title" style="font-size: 1.6rem; font-weight: 800; color: white;">April Site Visits</h2>
                            <p id="builder-report-meta" style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.1rem;"></p>
                        </div>
                    </div>
                    <div style="display: flex; gap: 0.75rem;" id="builder-actions-container">
                        <!-- Actions injected here dynamically based on role/status (e.g. Save Draft, Submit, Return, Approve, Reject) -->
                    </div>
                </div>

                <!-- Splitting Builder into left summary/claims and right documents/audit -->
                <div style="display: grid; grid-template-columns: 1.8fr 1fr; gap: 2rem; align-items: start;">
                    <!-- Left: Report Metadata & Claims Table -->
                    <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                        <!-- Report stats banner -->
                        <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--glass-border); border-radius: 16px; padding: 1.25rem; display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; text-align: center;">
                            <div style="border-right: 1px solid rgba(255,255,255,0.05);">
                                <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Total Claimed</span>
                                <div id="stat-total-claimed" style="font-size: 1.3rem; font-weight: 700; color: white; margin-top: 0.2rem;">$0.00</div>
                            </div>
                            <div style="border-right: 1px solid rgba(255,255,255,0.05);">
                                <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Reimbursable</span>
                                <div id="stat-total-reimbursable" style="font-size: 1.3rem; font-weight: 700; color: var(--success); margin-top: 0.2rem;">$0.00</div>
                            </div>
                            <div style="border-right: 1px solid rgba(255,255,255,0.05);">
                                <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Exceptions</span>
                                <div id="stat-policy-exceptions" style="font-size: 1.3rem; font-weight: 700; color: #fb7185; margin-top: 0.2rem;">0</div>
                            </div>
                            <div>
                                <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Missing Receipts</span>
                                <div id="stat-missing-documents" style="font-size: 1.3rem; font-weight: 700; color: #f59e0b; margin-top: 0.2rem;">0</div>
                            </div>
                        </div>

                        <!-- Return reason banner (if returned) -->
                        <div id="builder-return-reason-banner" style="display: none; background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 12px; padding: 1rem; color: #fda4af;">
                            <strong>Returned by Reviewer:</strong> <span id="builder-return-reason-text"></span>
                        </div>

                        <!-- Line Items Header -->
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="font-size: 1.2rem; font-weight: 700; color: white;">Expense Line Items</h3>
                            <button class="btn btn-primary" id="btn-add-line-item" onclick="openClaimFormModal()" style="padding: 0.5rem 1rem; font-size: 0.85rem; border-radius: 8px;">
                                + Add Expense Claim
                            </button>
                        </div>

                        <!-- Claims Table -->
                        <div style="background: var(--glass-bg); backdrop-filter: blur(12px); border: 1px solid var(--glass-border); border-radius: 16px; overflow: hidden;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem;">
                                <thead>
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); color: var(--text-muted); background: rgba(0,0,0,0.2);">
                                        <th style="padding: 0.8rem 1rem;">Category</th>
                                        <th style="padding: 0.8rem 1rem;">Date</th>
                                        <th style="padding: 0.8rem 1rem;">Amount</th>
                                        <th style="padding: 0.8rem 1rem;">Compliance</th>
                                        <th style="padding: 0.8rem 1rem;">Receipt Status</th>
                                        <th style="padding: 0.8rem 1rem; text-align: right;" class="builder-actions-column">Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="builder-claims-tbody">
                                    <!-- Claims populated here -->
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Right: GCS Receipts Hub & Audit Log -->
                    <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                        <!-- Bulk Receipt Upload zone (only visible for drafts) -->
                        <div id="builder-upload-container" style="background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 16px; padding: 1.5rem;">
                            <h3 style="font-size: 1.1rem; font-weight: 700; color: white; margin-bottom: 0.5rem;">Receipt Dossier</h3>
                            <p style="font-size: 0.8rem; color: var(--text-muted);">Bulk upload receipts/PDFs. You can assign them to specific claims below.</p>
                            
                            <div class="dropzone" id="bulk-receipt-dropzone" onclick="triggerBulkFileInput()">
                                <span style="font-size: 1.5rem; display: block; margin-bottom: 0.5rem;">📁</span>
                                <span style="font-weight: 500; font-size: 0.85rem;">Drag & drop files or click to upload</span>
                                <span style="display: block; font-size: 0.72rem; color: var(--text-muted); margin-top: 0.2rem;">PDF, PNG, JPG (Max 5MB)</span>
                                <input type="file" id="bulk-receipt-file-input" multiple style="display: none;" onchange="handleBulkReceiptsSelect(this.files)">
                            </div>
                        </div>

                        <!-- Unassigned/Supporting documents list -->
                        <div id="builder-documents-container" style="background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 16px; padding: 1.5rem;">
                            <h3 style="font-size: 1.1rem; font-weight: 700; color: white; margin-bottom: 0.5rem;">Report Documents</h3>
                            <div id="builder-documents-list" style="display: flex; flex-direction: column; gap: 0.75rem; margin-top: 1rem;">
                                <!-- Document items populated dynamically -->
                            </div>
                        </div>

                        <!-- Audit Log / Timeline for this report -->
                        <div style="background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 16px; padding: 1.5rem;">
                            <h3 style="font-size: 1.1rem; font-weight: 700; color: white; margin-bottom: 0.75rem;">Report Lifecycle Timeline</h3>
                            <div id="builder-audit-list" style="display: flex; flex-direction: column; gap: 1rem; border-left: 2px solid rgba(255,255,255,0.05); padding-left: 1rem; margin-left: 0.5rem; max-height: 300px; overflow-y: auto;">
                                <!-- Audit entries populated dynamically -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
"""

# 4. Define Slide Panel and Modals to append before </body>
html_modals = """
    <!-- New Report Sliding Drawer -->
    <div id="drawer-new-report" class="slider-panel">
        <div class="slider-header">
            <h2 style="font-size: 1.4rem; font-weight: 800; color: white;">New Expense Report</h2>
            <button onclick="closeNewReportDrawer()" style="background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer;">&times;</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 1.25rem;">
            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Report Title</label>
                <input type="text" id="report-title-input" placeholder="e.g. April Site Visits" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 10px; padding: 0.75rem; color: white; font-family: inherit;">
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Start Date</label>
                    <input type="date" id="report-start-date" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 10px; padding: 0.75rem; color: white; font-family: inherit;">
                </div>
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">End Date</label>
                    <input type="date" id="report-end-date" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 10px; padding: 0.75rem; color: white; font-family: inherit;">
                </div>
            </div>
            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Travel Week (Optional)</label>
                <input type="text" id="report-travel-week" placeholder="e.g. Week 15" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 10px; padding: 0.75rem; color: white; font-family: inherit;">
            </div>
            
            <!-- Employee Selector for Finance Admin Testing -->
            <div id="drawer-employee-selector" style="display: none; background: rgba(99,102,241,0.05); border: 1px solid rgba(99,102,241,0.15); padding: 1rem; border-radius: 12px; margin-top: 0.5rem;">
                <label style="font-size: 0.75rem; color: #a5b4fc; text-transform: uppercase; font-weight: 700; display: block; margin-bottom: 0.4rem;">Demo Employee Emulation</label>
                <select id="drawer-emulated-employee" style="width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(99,102,241,0.3); border-radius: 8px; padding: 0.5rem; color: white; font-family: inherit;">
                    <option value="">Use Logged-in User</option>
                    <option value="cra001.manager001@demo-company.com">CRA 001 Manager 001 (cra001.manager001@demo-company.com)</option>
                </select>
                <p style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.3rem;">Simulates creating a report for the demo employee.</p>
            </div>

            <button class="btn btn-primary" onclick="submitCreateReport()" style="margin-top: 1.5rem; padding: 1rem; font-weight: 600; border-radius: 10px;">
                Create Draft Report
            </button>
        </div>
    </div>

    <!-- Claim Form Overlay Modal -->
    <div class="slide-overlay" id="claim-modal-overlay"></div>
    <div id="modal-claim-form" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(0.9); background: rgba(10, 11, 26, 0.98); backdrop-filter: blur(20px); border: 1px solid var(--glass-border); border-radius: 24px; padding: 2rem; width: 550px; max-height: 90vh; overflow-y: auto; z-index: 150; opacity: 0; pointer-events: none; transition: var(--transition); box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.75rem;">
            <h2 id="claim-modal-title" style="font-size: 1.4rem; font-weight: 800; color: white;">Add Expense Claim</h2>
            <button onclick="closeClaimFormModal()" style="background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer;">&times;</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 1rem;">
            <input type="hidden" id="claim-id-hidden">
            
            <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 1rem;">
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Category</label>
                    <select id="claim-category" onchange="onClaimCategoryChange()" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                        <option value="Flight">Flight</option>
                        <option value="Hotel">Hotel</option>
                        <option value="Meals">Meals</option>
                        <option value="Rental Car">Rental Car</option>
                        <option value="Rental Car Gas">Rental Car Gas</option>
                        <option value="Parking">Parking</option>
                        <option value="Tolls">Tolls</option>
                        <option value="Mileage">Mileage</option>
                        <option value="Office Supplies">Office Supplies</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Expense Date</label>
                    <input type="date" id="claim-date" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1.5fr 1fr; gap: 1rem;">
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Amount</label>
                    <input type="number" id="claim-amount" step="0.01" placeholder="0.00" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                </div>
                <div>
                    <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Currency</label>
                    <select id="claim-currency" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                        <option value="USD">USD ($)</option>
                        <option value="EUR">EUR (€)</option>
                        <option value="GBP">GBP (£)</option>
                        <option value="CAD">CAD ($)</option>
                    </select>
                </div>
            </div>

            <!-- Dynamic Fields for Hotel (Dates) -->
            <div id="claim-hotel-fields" style="display: none; grid-template-columns: 1fr 1fr; gap: 1rem; background: rgba(255,255,255,0.02); padding: 0.75rem; border-radius: 8px; border: 1px solid var(--glass-border);">
                <div>
                    <label style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Check-in Date</label>
                    <input type="date" id="claim-hotel-in" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 6px; padding: 0.5rem; color: white; font-size: 0.8rem;">
                </div>
                <div>
                    <label style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Check-out Date</label>
                    <input type="date" id="claim-hotel-out" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 6px; padding: 0.5rem; color: white; font-size: 0.8rem;">
                </div>
            </div>

            <!-- Dynamic Fields for Transportation/Mileage -->
            <div id="claim-transportation-fields" style="display: none; background: rgba(255,255,255,0.02); padding: 0.75rem; border-radius: 8px; border: 1px solid var(--glass-border); display: flex; flex-direction: column; gap: 0.75rem;">
                <div>
                    <label style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Transportation Type</label>
                    <select id="claim-trans-type" onchange="onClaimTransTypeChange()" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 6px; padding: 0.5rem; color: white; font-size: 0.8rem;">
                        <option value="">-- Select Type --</option>
                        <option value="personal_vehicle">Personal Vehicle</option>
                        <option value="rental_car">Rental Car</option>
                        <option value="company_vehicle">Company Vehicle</option>
                        <option value="public_transit">Public Transit</option>
                    </select>
                </div>
                <div id="claim-mileage-row" style="display: none; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div>
                        <label style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Mileage (Miles)</label>
                        <input type="number" id="claim-mileage" placeholder="0" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 6px; padding: 0.5rem; color: white; font-size: 0.8rem;">
                    </div>
                    <div>
                        <label style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Gas Cost Inside Amount</label>
                        <input type="number" id="claim-gas-cost" step="0.01" placeholder="0.00" style="width: 100%; background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 6px; padding: 0.5rem; color: white; font-size: 0.8rem;">
                    </div>
                </div>
            </div>

            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Business Purpose</label>
                <input type="text" id="claim-purpose" placeholder="e.g. Client presentation site visit" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
            </div>

            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Description / Details</label>
                <textarea id="claim-description" rows="3" placeholder="Specify locations visited or other details..." style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit; resize: none;"></textarea>
            </div>

            <!-- Single document upload for this claim (saves directly to GCS and auto-assigns) -->
            <div id="claim-receipt-upload-row">
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.3rem;">Direct Receipt Upload</label>
                <input type="file" id="claim-receipt-file" style="width: 100%; color: var(--text-muted); font-size: 0.8rem;">
                <p style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.2rem;">Directly attach a receipt image/PDF to this claim.</p>
            </div>

            <button class="btn btn-primary" onclick="submitClaimForm()" style="margin-top: 1rem; padding: 0.8rem; font-weight: 600; border-radius: 8px;">
                Save Claim Line Item
            </button>
        </div>
    </div>

    <!-- Assign Document Overlay Modal -->
    <div class="slide-overlay" id="assign-modal-overlay"></div>
    <div id="modal-assign-receipt" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(0.9); background: rgba(10, 11, 26, 0.98); backdrop-filter: blur(20px); border: 1px solid var(--glass-border); border-radius: 24px; padding: 2rem; width: 450px; z-index: 150; opacity: 0; pointer-events: none; transition: var(--transition); box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.75rem;">
            <h2 style="font-size: 1.3rem; font-weight: 800; color: white;">Assign Document</h2>
            <button onclick="closeAssignModal()" style="background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer;">&times;</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 1.25rem;">
            <input type="hidden" id="assign-doc-id">
            <div>
                <strong style="color: var(--text-muted); font-size: 0.8rem;">Selected Document:</strong>
                <p id="assign-doc-filename" style="color: white; font-weight: 600; font-size: 0.95rem; margin-top: 0.2rem;"></p>
            </div>
            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Assign to Line Item</label>
                <select id="assign-claim-select" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                    <!-- Claims list options populated dynamically -->
                </select>
            </div>
            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Document Classification Type</label>
                <select id="assign-doc-type" style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit;">
                    <option value="receipt">Standard Receipt</option>
                    <option value="office_receipt">Office Supplies Receipt</option>
                    <option value="parking_receipt">Parking Receipt</option>
                    <option value="hotel_receipt">Hotel Lodging Folio</option>
                    <option value="flight_ticket_receipt">Flight Ticket Invoice</option>
                    <option value="manager_approval_letter">Manager Prior Approval Letter</option>
                    <option value="other">Supporting Document / Other</option>
                </select>
            </div>
            <button class="btn btn-primary" onclick="submitAssignReceipt()" style="margin-top: 1rem; padding: 0.8rem; font-weight: 600; border-radius: 8px;">
                Confirm Assignment
            </button>
        </div>
    </div>

    <!-- Return Comments Modal -->
    <div class="slide-overlay" id="return-modal-overlay"></div>
    <div id="modal-return-comments" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(0.9); background: rgba(10, 11, 26, 0.98); backdrop-filter: blur(20px); border: 1px solid var(--glass-border); border-radius: 24px; padding: 2rem; width: 450px; z-index: 150; opacity: 0; pointer-events: none; transition: var(--transition); box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.75rem;">
            <h2 style="font-size: 1.3rem; font-weight: 800; color: white;">Return Report to Employee</h2>
            <button onclick="closeReturnModal()" style="background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer;">&times;</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 1.25rem;">
            <input type="hidden" id="return-report-id">
            <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; display: block; margin-bottom: 0.4rem;">Reason for Returning</label>
                <textarea id="return-reason-input" rows="4" placeholder="Explain what needs to be fixed (e.g. missing flight receipt or incorrect mileage)..." style="width: 100%; background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.6rem; color: white; font-family: inherit; resize: none;"></textarea>
            </div>
            <button class="btn btn-danger" onclick="submitReturnReport()" style="padding: 0.8rem; font-weight: 600; border-radius: 8px; background: var(--danger); border-color: var(--danger);">
                Return to Employee
            </button>
        </div>
    </div>
"""

# ---- APPLY EDITS TO main_content ----

# A. Insert CSS inside the dashboard </style> block
dashboard_style_pattern = re.compile(r'(/\* Beautiful glassmorphic tab bar \*/|/\* Styling for compliance indicators \*/|.*)?</style>\\s*</head>\\s*<body>\\s*<div class="glow-spot-1"', re.DOTALL)
# Wait, let's just find the exact string: "</style>\n</head>\n<body>\n    <div class=\"glow-spot-1\"" and replace it with our CSS + style end + body!
# Let's verify the lines:
# 5318: </style>
# 5319: </head>
# 5320: <body>
# 5321:     <div class="glow-spot-1"
css_target = "</style>\n</head>\n<body>\n    <div class=\"glow-spot-1\""
# Wait, inside main.py there might be spaces/newlines. Let's do a direct replacement!
target_css_end = "</style>\n</head>\n<body>\n    <div class=\"glow-spot-1\""
if css_target in main_content:
    print("Found exact CSS anchor!")
    main_content = main_content.replace(css_target, css_code + '\n</style>\n</head>\n<body>\n    <div class="glow-spot-1"')
else:
    # Try regex or flexible spacing
    print("Exact CSS anchor not found, using flexible match...")
    pattern = re.compile(r'</style>\s*</head>\s*<body>\s*<div class=["\']glow-spot-1["\']')
    m = pattern.search(main_content)
    if m:
        start, end = m.span()
        matched_str = m.group(0)
        print(f"Matched flexible CSS anchor: {matched_str}")
        main_content = main_content[:start] + css_code + "\\n" + matched_str + main_content[end:]
    else:
        print("CRITICAL: CSS anchor not found!")

# B. Insert Tab Button inside the tab bar
tab_target = '<button class="tab-btn" id="tab-submit" onclick="switchTab(\'submit\')"'
if tab_target in main_content:
    print("Found exact Tab Button anchor!")
    tab_reports_btn = """<button class="tab-btn" id="tab-reports" onclick="switchTab('reports')" style="background: none; border: none; color: var(--text-muted); font-family: inherit; font-size: 1.05rem; font-weight: 600; padding: 0.5rem 1rem; cursor: pointer; position: relative; transition: var(--transition);">
            My Reports
        </button>
        """
    main_content = main_content.replace(tab_target, tab_reports_btn + tab_target)
else:
    print("CRITICAL: Tab Button anchor not found!")

# C. Insert HTML reports section inside <main>
main_section_target = "<!-- 1. Pending Approvals Section -->"
if main_section_target in main_content:
    print("Found exact Main Section anchor!")
    main_content = main_content.replace(main_section_target, html_reports_section + "\\n        " + main_section_target)
else:
    print("CRITICAL: Main Section anchor not found!")

# D. Append new Modals/Drawers before </body></html>
body_end_target = "</body>\n</html>"
if body_end_target in main_content:
    print("Found exact Body End anchor!")
    # Make sure we do it only for the first occurrence or handle properly. Let's find the last occurrence!
    idx = main_content.rfind(body_end_target)
    if idx != -1:
        main_content = main_content[:idx] + html_modals + "\\n" + main_content[idx:]
        print("Modals appended successfully.")
else:
    print("CRITICAL: Body End anchor not found!")

# E. Append JS code inside the main script block
js_end_target = 'window.addEventListener("DOMContentLoaded", () => {'
if js_end_target in main_content:
    print("Found JS script end anchor!")
    # Append JS code before DOMContentLoaded event listener
    main_content = main_content.replace(js_end_target, js_code + "\\n\\n        " + js_end_target)
else:
    print("CRITICAL: JS script end anchor not found!")

# F. Update DOMContentLoaded role replacements in python code (around line 7793)
dom_replace_target = """            // Apply role-based visibility rules
            if (USER_ROLE === "employee") {
                document.getElementById("tab-pending").style.display = "none";
                document.getElementById("tab-audit").style.display = "none";
                switchTab('submit');
            } else if (USER_ROLE === "manager") {
                document.getElementById("tab-submit").style.display = "none";
                document.getElementById("tab-audit").style.display = "none";
                fetchPendingApprovals();
            } else {
                fetchPendingApprovals();
            }"""

dom_replace_new = """            // Apply role-based visibility rules
            if (USER_ROLE === "employee") {
                document.getElementById("tab-pending").style.display = "none";
                document.getElementById("tab-audit").style.display = "none";
                switchTab('reports');
            } else if (USER_ROLE === "manager") {
                document.getElementById("tab-submit").style.display = "none";
                document.getElementById("tab-audit").style.display = "none";
                switchTab('pending');
            } else {
                switchTab('reports');
            }"""

if dom_replace_target in main_content:
    print("Found exact DOMContentLoaded replace target!")
    main_content = main_content.replace(dom_replace_target, dom_replace_new)
else:
    # Flexible match for whitespace
    print("Exact DOMContentLoaded target not found, searching with regex...")
    pattern = re.compile(r"if\s*\(\s*USER_ROLE\s*===\s*['\"]employee['\"]\s*\)\s*\{.*?switchTab\(\s*['\"]submit['\"]\s*\);.*?\}\s*else\s*if\s*\(\s*USER_ROLE\s*===\s*['\"]manager['\"]\s*\)\s*\{.*?fetchPendingApprovals\(\s*\);.*?\}\s*else\s*\{\s*fetchPendingApprovals\(\s*\);.*?\}", re.DOTALL)
    m = pattern.search(main_content)
    if m:
        print("Found regex match for DOMContentLoaded!")
        main_content = main_content[:m.start()] + dom_replace_new + main_content[m.end():]
    else:
        print("CRITICAL: DOMContentLoaded replace target not found!")

# Write updated content back to main.py
with open("submission_frontend/main.py", "w", encoding="utf-8") as f:
    f.write(main_content)

print("Upgrade complete and main.py written successfully!")
