        function safeNumber(value) {
            if (value === undefined || value === null || value === "") return 0;
            const parsed = parseFloat(value);
            return isNaN(parsed) ? 0 : parsed;
        }

        function formatMoney(value) {
            try {
                const num = safeNumber(value);
                return "$" + num.toFixed(2);
            } catch (e) {
                console.warn("formatMoney failed for value:", value, e);
                return "$0.00";
            }
        }

        // cachedClaims is defined globally in the inline script of dashboard.html
        let lineItems = [];
        let lineItemDocs = {};
        let allExpenses = [];
        let queryRowCounter = 0;

        const DOC_TYPES = {
            receipt: { label: "General Receipt", icon: "📄" },
            hotel_receipt: { label: "Hotel Receipt", icon: "🏨" },
            flight_ticket_receipt: { label: "Flight Receipt", icon: "✈️" },
            manager_approval_letter: { label: "Manager Approval Letter", icon: "✉️" },
            office_receipt: { label: "Office Receipt", icon: "💼" },
            parking_receipt: { label: "Parking Receipt", icon: "🚗" },
            mileage_log: { label: "Mileage Log", icon: "🗺️" },
            rental_receipt: { label: "Rental Receipt", icon: "🔑" },
            gas_receipt: { label: "Gas Receipt", icon: "⛽" },
            toll_receipt: { label: "Toll Receipt", icon: "🪙" }
        };

        function generateUUID() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        function titleCase(str) {
            if (!str) return "";
            return str.split(/[\._]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        }

        function initSubmitForm() {
            if (lineItems.length === 0) {
                resetSubmissionForm();
            }
        }

        function createDefaultLineItem() {
            return {
                claimId: generateUUID(),
                category: "",
                amount: "",
                currency: "USD",
                expenseDate: new Date().toISOString().substring(0, 10),
                vendor: "",
                description: ""
            };
        }

        function syncLineItemsFromDOM() {
            lineItems.forEach(item => {
                const claimId = item.claimId;
                
                const catEl = document.getElementById(`form-category-${claimId}`);
                if (catEl) item.category = catEl.value;
                
                const amtEl = document.getElementById(`form-amount-${claimId}`);
                if (amtEl) item.amount = amtEl.value;
                
                const curEl = document.getElementById(`form-currency-${claimId}`);
                if (curEl) item.currency = curEl.value;
                
                const dateEl = document.getElementById(`form-expense-date-${claimId}`);
                if (dateEl) item.expenseDate = dateEl.value;
                
                const vendEl = document.getElementById(`form-vendor-${claimId}`);
                if (vendEl) item.vendor = vendEl.value;
                
                const descEl = document.getElementById(`form-description-${claimId}`);
                if (descEl) item.description = descEl.value;
                
                // Travel fields
                const startEl = document.getElementById(`form-travel-start-${claimId}`);
                if (startEl) item.travel_start_date = startEl.value;
                
                const endEl = document.getElementById(`form-travel-end-${claimId}`);
                if (endEl) item.travel_end_date = endEl.value;
                
                const cityEl = document.getElementById(`form-city-${claimId}`);
                if (cityEl) item.city = cityEl.value;
                
                const stateEl = document.getElementById(`form-state-${claimId}`);
                if (stateEl) item.state = stateEl.value;
                
                const countryEl = document.getElementById(`form-country-${claimId}`);
                if (countryEl) item.country = countryEl.value;
                
                const mealsEl = document.getElementById(`form-claimed-meals-${claimId}`);
                if (mealsEl) item.claimed_meals = mealsEl.value;
                
                const lodgEl = document.getElementById(`form-claimed-lodging-${claimId}`);
                if (lodgEl) item.claimed_lodging = lodgEl.value;
                
                const incEl = document.getElementById(`form-claimed-incidentals-${claimId}`);
                if (incEl) item.claimed_incidentals = incEl.value;
                
                const chinEl = document.getElementById(`form-check-in-${claimId}`);
                if (chinEl) item.check_in_date = chinEl.value;
                
                const choutEl = document.getElementById(`form-check-out-${claimId}`);
                if (choutEl) item.check_out_date = choutEl.value;
                
                // Transport fields
                const transTypeEl = document.getElementById(`form-trans-type-${claimId}`);
                if (transTypeEl) item.transportation_type = transTypeEl.value;
                
                const tripDateEl = document.getElementById(`form-trip-date-${claimId}`);
                if (tripDateEl) item.trip_date = tripDateEl.value;
                
                const startLocEl = document.getElementById(`form-start-loc-${claimId}`);
                if (startLocEl) item.start_location_label = startLocEl.value;
                
                const startAddrEl = document.getElementById(`form-start-addr-${claimId}`);
                if (startAddrEl) item.start_address = startAddrEl.value;
                
                const destLocEl = document.getElementById(`form-dest-loc-${claimId}`);
                if (destLocEl) item.destination_location_label = destLocEl.value;
                
                const destAddrEl = document.getElementById(`form-dest-addr-${claimId}`);
                if (destAddrEl) item.destination_address = destAddrEl.value;
                
                const tripTypeEl = document.getElementById(`form-trip-type-${claimId}`);
                if (tripTypeEl) item.trip_type = tripTypeEl.value;
                
                const bizMilesEl = document.getElementById(`form-biz-miles-${claimId}`);
                if (bizMilesEl) item.business_miles = bizMilesEl.value;
                
                const entMilesEl = document.getElementById(`form-entered-miles-${claimId}`);
                if (entMilesEl) item.employee_entered_miles = entMilesEl.value;
                
                const rentalStartEl = document.getElementById(`form-rental-start-${claimId}`);
                if (rentalStartEl) item.rental_start_date = rentalStartEl.value;
                
                const rentalEndEl = document.getElementById(`form-rental-end-${claimId}`);
                if (rentalEndEl) item.rental_end_date = rentalEndEl.value;
                
                const rentalCostEl = document.getElementById(`form-rental-cost-${claimId}`);
                if (rentalCostEl) item.rental_cost = rentalCostEl.value;
                
                const gasCostEl = document.getElementById(`form-gas-cost-${claimId}`);
                if (gasCostEl) item.gas_cost = gasCostEl.value;
                
                const parkCostEl = document.getElementById(`form-parking-cost-${claimId}`);
                if (parkCostEl) item.parking_cost = parkCostEl.value;
                
                const tollCostEl = document.getElementById(`form-toll-cost-${claimId}`);
                if (tollCostEl) item.toll_cost = tollCostEl.value;
                
                const linkedRentalEl = document.getElementById(`form-linked-rental-${claimId}`);
                if (linkedRentalEl) item.linked_rental_claim_id = linkedRentalEl.value;
            });
        }

        function updateOverallRunningTotal() {
            let total = 0;
            lineItems.forEach(item => {
                const amtEl = document.getElementById(`form-amount-${item.claimId}`);
                const val = amtEl ? safeNumber(amtEl.value) : safeNumber(item.amount);
                total += val;
            });
            const totalEl = document.getElementById("overall-running-total");
            if (totalEl) {
                totalEl.textContent = "Report Total: " + formatMoney(total);
            }
        }

        function addLineItem() {
            syncLineItemsFromDOM();
            lineItems.push(createDefaultLineItem());
            renderLineItems();
            updateOverallRunningTotal();
            triggerLivePreview();
        }

        function removeLineItem(claimId) {
            if (lineItems.length <= 1) return;
            syncLineItemsFromDOM();
            lineItems = lineItems.filter(item => item.claimId !== claimId);
            delete lineItemDocs[claimId];
            renderLineItems();
            updateOverallRunningTotal();
            triggerLivePreview();
        }

        function renderPortalUploadGridForClaim(claimId) {
            const grid = document.getElementById(`portal-upload-grid-${claimId}`);
            if (!grid) return;
            grid.innerHTML = "";
            Object.keys(DOC_TYPES).forEach(docType => {
                const config = DOC_TYPES[docType];
                const div = document.createElement("div");
                div.className = "upload-dropzone";
                div.id = `dz-${docType}-${claimId}`;
                
                const uploadedName = lineItemDocs[claimId] && lineItemDocs[claimId][docType];
                if (uploadedName) {
                    div.classList.add("uploaded");
                    div.innerHTML = `
                        <input type="file" id="file-input-${docType}-${claimId}" onchange="uploadPortalFile('${claimId}', '${docType}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display: none;">
                        <span class="dropzone-icon" style="color: #34d399;">✓</span>
                        <span class="dropzone-title">${config.label}</span>
                        <span class="dropzone-status" style="color: #34d399;">Uploaded</span>
                        <span style="font-size: 0.65rem; color: var(--text-muted); margin-top: -0.2rem; text-overflow: ellipsis; white-space: nowrap; overflow: hidden; max-width: 160px; display: block; margin-left: auto; margin-right: auto;">${escapeHtml(uploadedName)}</span>
                    `;
                } else {
                    div.innerHTML = `
                        <input type="file" id="file-input-${docType}-${claimId}" onchange="uploadPortalFile('${claimId}', '${docType}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display: none;">
                        <span class="dropzone-icon">${config.icon}</span>
                        <span class="dropzone-title">${config.label}</span>
                        <span class="dropzone-status" style="color: var(--text-muted);" id="dz-status-${docType}-${claimId}">Empty</span>
                    `;
                }
                
                div.onclick = (e) => {
                    if (e.target.tagName !== 'INPUT') {
                        const inp = document.getElementById(`file-input-${docType}-${claimId}`);
                        if (inp) inp.click();
                    }
                };
                grid.appendChild(div);
            });
        }

        async function uploadPortalFile(claimId, docType, inputElement) {
            if (!inputElement.files || inputElement.files.length === 0) return;
            const file = inputElement.files[0];
            const dz = document.getElementById(`dz-${docType}-${claimId}`);
            const originalHTML = dz.innerHTML;
            
            dz.style.pointerEvents = "none";
            dz.innerHTML = `
                <div class="spinner" style="width:24px; height:24px; border-width:2px; margin-bottom: 0.5rem; margin-left: auto; margin-right: auto;"></div>
                <span style="font-size: 0.75rem; color: var(--text-muted);">Uploading...</span>
            `;
            
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const response = await fetch(`/api/employee/claims/${claimId}/documents/${docType}`, {
                    method: "POST",
                    body: formData
                });
                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "Upload failed");
                }
                
                showToast(`${file.name} uploaded successfully!`, "success");
                
                if (!lineItemDocs[claimId]) {
                    lineItemDocs[claimId] = {};
                }
                lineItemDocs[claimId][docType] = file.name;
                
                dz.classList.add("uploaded");
                dz.innerHTML = `
                    <input type="file" id="file-input-${docType}-${claimId}" onchange="uploadPortalFile('${claimId}', '${docType}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display: none;">
                    <span class="dropzone-icon" style="color: #34d399;">✓</span>
                    <span class="dropzone-title">${DOC_TYPES[docType].label}</span>
                    <span class="dropzone-status" style="color: #34d399;">Uploaded</span>
                    <span style="font-size: 0.65rem; color: var(--text-muted); margin-top: -0.2rem; text-overflow: ellipsis; white-space: nowrap; overflow: hidden; max-width: 160px; display: block; margin-left: auto; margin-right: auto;">${escapeHtml(file.name)}</span>
                `;
                
                triggerLivePreview();
            } catch (err) {
                console.error("Portal upload failed", err);
                showToast("Upload failed: " + err.message, "error");
                dz.innerHTML = originalHTML;
            } finally {
                dz.style.pointerEvents = "all";
            }
        }

        function handleLineItemCategoryChange(claimId, category) {
            const travelCard = document.getElementById(`card-travel-fields-${claimId}`);
            const transportCard = document.getElementById(`card-transport-fields-${claimId}`);
            
            const isTravel = ["meals", "lodging", "flight"].includes(category);
            const isTransport = ["transportation", "rental_car", "rental_car_gas", "parking", "tolls"].includes(category);
            
            if (travelCard) travelCard.style.display = isTravel ? "block" : "none";
            if (transportCard) transportCard.style.display = isTransport ? "block" : "none";
            
            const transTypeEl = document.getElementById(`form-trans-type-${claimId}`);
            if (transTypeEl) {
                if (category === "rental_car") {
                    transTypeEl.value = "rental_car";
                } else if (category === "rental_car_gas") {
                    transTypeEl.value = "rental_car_gas";
                } else if (category === "parking") {
                    transTypeEl.value = "parking";
                } else if (category === "tolls") {
                    transTypeEl.value = "tolls";
                } else if (category === "transportation") {
                    transTypeEl.value = "personal_vehicle";
                }
            }
            
            triggerLivePreview();
        }

        function renderLineItems() {
            const container = document.getElementById("line-items-container");
            if (!container) return;
            container.innerHTML = "";
            
            lineItems.forEach((item, index) => {
                const claimId = item.claimId;
                const isTravel = ["meals", "lodging", "flight"].includes(item.category);
                const isTransport = ["transportation", "rental_car", "rental_car_gas", "parking", "tolls"].includes(item.category);
                
                const card = document.createElement("div");
                card.className = "form-section-card";
                card.id = `line-item-card-${claimId}`;
                card.style.border = "1px solid rgba(255,255,255,0.08)";
                card.style.marginBottom = "1.5rem";
                
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 0.75rem 1.25rem; border-bottom: 1px solid rgba(255,255,255,0.05); margin: -1.25rem -1.25rem 1.25rem -1.25rem; border-top-left-radius: 12px; border-top-right-radius: 12px;">
                        <span style="font-weight: 700; color: #a5b4fc; font-size: 0.95rem; display: flex; align-items: center; gap: 0.5rem;">
                            <span>📍</span> Line Item #${index + 1}
                        </span>
                        ${lineItems.length > 1 ? `
                        <button type="button" class="btn btn-approve" onclick="removeLineItem('${claimId}')" style="background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); padding: 0.35rem 0.75rem; font-size: 0.75rem; border-radius: 6px; width: auto; height: auto; font-weight: 600;">
                            🗑️ Remove
                        </button>
                        ` : ''}
                    </div>
                    
                    <div class="form-grid">
                        <div class="form-group">
                            <label for="form-category-${claimId}">Expense Category</label>
                            <select id="form-category-${claimId}" required onchange="handleLineItemCategoryChange('${claimId}', this.value)">
                                <option value="">-- Choose Category --</option>
                                <option value="meals" ${item.category === 'meals' ? 'selected' : ''}>Meals</option>
                                <option value="lodging" ${item.category === 'lodging' ? 'selected' : ''}>Lodging</option>
                                <option value="flight" ${item.category === 'flight' ? 'selected' : ''}>Flight</option>
                                <option value="office_supplies" ${item.category === 'office_supplies' ? 'selected' : ''}>Office Supplies</option>
                                <option value="printing_supplies" ${item.category === 'printing_supplies' ? 'selected' : ''}>Printing Supplies</option>
                                <option value="parking" ${item.category === 'parking' ? 'selected' : ''}>Parking</option>
                                <option value="parking_citation" ${item.category === 'parking_citation' ? 'selected' : ''}>Parking Citation</option>
                                <option value="transportation" ${item.category === 'transportation' ? 'selected' : ''}>Transportation</option>
                                <option value="tolls" ${item.category === 'tolls' ? 'selected' : ''}>Tolls</option>
                                <option value="rental_car" ${item.category === 'rental_car' ? 'selected' : ''}>Rental Car</option>
                                <option value="rental_car_gas" ${item.category === 'rental_car_gas' ? 'selected' : ''}>Rental Car Gas</option>
                                <option value="other" ${item.category === 'other' ? 'selected' : ''}>Other</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="form-amount-${claimId}">Amount</label>
                            <input type="number" step="0.01" id="form-amount-${claimId}" placeholder="0.00" value="${item.amount || ''}" required oninput="updateOverallRunningTotal(); triggerLivePreview()">
                        </div>
                        <div class="form-group">
                            <label for="form-currency-${claimId}">Currency</label>
                            <select id="form-currency-${claimId}" required onchange="triggerLivePreview()">
                                <option value="USD" ${item.currency === 'USD' ? 'selected' : ''}>USD ($)</option>
                                <option value="EUR" ${item.currency === 'EUR' ? 'selected' : ''}>EUR (€)</option>
                                <option value="GBP" ${item.currency === 'GBP' ? 'selected' : ''}>GBP (£)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="form-expense-date-${claimId}">Expense Date</label>
                            <input type="date" id="form-expense-date-${claimId}" value="${item.expenseDate || ''}" required onchange="triggerLivePreview()">
                        </div>
                        <div class="form-group full-width">
                            <label for="form-vendor-${claimId}">Vendor / Merchant</label>
                            <input type="text" id="form-vendor-${claimId}" placeholder="e.g. ACME Corp" value="${item.vendor || ''}" required oninput="triggerLivePreview()">
                        </div>
                        <div class="form-group full-width">
                            <label for="form-description-${claimId}">Description</label>
                            <textarea id="form-description-${claimId}" rows="2" placeholder="e.g. Dinner with clients..." oninput="triggerLivePreview()">${item.description || ''}</textarea>
                        </div>
                    </div>
                    
                    <div class="form-section-card" id="card-travel-fields-${claimId}" style="display: ${isTravel ? 'block' : 'none'}; margin-top: 1.25rem; margin-bottom: 0; border: 1px solid rgba(165, 180, 252, 0.15); background: rgba(165, 180, 252, 0.02); padding: 1.25rem;">
                        <div class="form-section-title" style="font-size: 0.9rem; padding-bottom: 0.5rem; margin-bottom: 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.05); color: #a5b4fc;">
                            <span class="section-icon">✈️</span> Travel / Per Diem Details
                        </div>
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="form-travel-start-${claimId}">Travel Start Date</label>
                                <input type="date" id="form-travel-start-${claimId}" value="${item.travel_start_date || ''}" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-travel-end-${claimId}">Travel End Date</label>
                                <input type="date" id="form-travel-end-${claimId}" value="${item.travel_end_date || ''}" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-city-${claimId}">City</label>
                                <input type="text" id="form-city-${claimId}" placeholder="New York" value="${item.city || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-state-${claimId}">State</label>
                                <input type="text" id="form-state-${claimId}" placeholder="NY" value="${item.state || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-country-${claimId}">Country</label>
                                <input type="text" id="form-country-${claimId}" value="${item.country || 'US'}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-claimed-meals-${claimId}">Claimed Meals Total</label>
                                <input type="number" step="0.01" id="form-claimed-meals-${claimId}" placeholder="0.00" value="${item.claimed_meals || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-claimed-lodging-${claimId}">Claimed Lodging Total</label>
                                <input type="number" step="0.01" id="form-claimed-lodging-${claimId}" placeholder="0.00" value="${item.claimed_lodging || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-claimed-incidentals-${claimId}">Claimed Incidentals Total</label>
                                <input type="number" step="0.01" id="form-claimed-incidentals-${claimId}" placeholder="0.00" value="${item.claimed_incidentals || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-check-in-${claimId}">Hotel Check-In Date</label>
                                <input type="date" id="form-check-in-${claimId}" value="${item.check_in_date || ''}" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-check-out-${claimId}">Hotel Check-Out Date</label>
                                <input type="date" id="form-check-out-${claimId}" value="${item.check_out_date || ''}" onchange="triggerLivePreview()">
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-section-card" id="card-transport-fields-${claimId}" style="display: ${isTransport ? 'block' : 'none'}; margin-top: 1.25rem; margin-bottom: 0; border: 1px solid rgba(165, 180, 252, 0.15); background: rgba(165, 180, 252, 0.02); padding: 1.25rem;">
                        <div class="form-section-title" style="font-size: 0.9rem; padding-bottom: 0.5rem; margin-bottom: 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.05); color: #a5b4fc;">
                            <span class="section-icon">🚗</span> Transportation Details
                        </div>
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="form-trans-type-${claimId}">Transportation Type</label>
                                <select id="form-trans-type-${claimId}" onchange="triggerLivePreview()">
                                    <option value="">-- Choose Type --</option>
                                    <option value="personal_vehicle" ${item.transportation_type === 'personal_vehicle' ? 'selected' : ''}>Personal Vehicle</option>
                                    <option value="rental_car" ${item.transportation_type === 'rental_car' ? 'selected' : ''}>Rental Car</option>
                                    <option value="rental_car_gas" ${item.transportation_type === 'rental_car_gas' ? 'selected' : ''}>Rental Car Gas</option>
                                    <option value="parking" ${item.transportation_type === 'parking' ? 'selected' : ''}>Parking</option>
                                    <option value="tolls" ${item.transportation_type === 'tolls' ? 'selected' : ''}>Tolls</option>
                                    <option value="mixed" ${item.transportation_type === 'mixed' ? 'selected' : ''}>Mixed</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="form-trip-date-${claimId}">Trip Date</label>
                                <input type="date" id="form-trip-date-${claimId}" value="${item.trip_date || ''}" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-start-loc-${claimId}">Start Location Label</label>
                                <input type="text" id="form-start-loc-${claimId}" placeholder="e.g. home" value="${item.start_location_label || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-start-addr-${claimId}">Start Address</label>
                                <input type="text" id="form-start-addr-${claimId}" placeholder="Raleigh, NC" value="${item.start_address || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-dest-loc-${claimId}">Destination Location Label</label>
                                <input type="text" id="form-dest-loc-${claimId}" placeholder="e.g. client_site" value="${item.destination_location_label || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-dest-addr-${claimId}">Destination Address</label>
                                <input type="text" id="form-dest-addr-${claimId}" placeholder="Charlotte, NC" value="${item.destination_address || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-trip-type-${claimId}">Trip Type</label>
                                <select id="form-trip-type-${claimId}" onchange="triggerLivePreview()">
                                    <option value="one_way" ${item.trip_type === 'one_way' ? 'selected' : ''}>One Way</option>
                                    <option value="round_trip" ${item.trip_type === 'round_trip' ? 'selected' : ''}>Round Trip</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="form-biz-miles-${claimId}">Business Miles</label>
                                <input type="number" step="0.1" id="form-biz-miles-${claimId}" placeholder="0.0" value="${item.business_miles || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-entered-miles-${claimId}">Employee Entered Miles</label>
                                <input type="number" step="0.1" id="form-entered-miles-${claimId}" placeholder="0.0" value="${item.employee_entered_miles || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-rental-start-${claimId}">Rental Start Date</label>
                                <input type="date" id="form-rental-start-${claimId}" value="${item.rental_start_date || ''}" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-rental-end-${claimId}">Rental End Date</label>
                                <input type="date" id="form-rental-end-${claimId}" value="${item.rental_end_date || ''}" onchange="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-rental-cost-${claimId}">Rental Cost</label>
                                <input type="number" step="0.01" id="form-rental-cost-${claimId}" placeholder="0.00" value="${item.rental_cost || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-gas-cost-${claimId}">Gas Cost</label>
                                <input type="number" step="0.01" id="form-gas-cost-${claimId}" placeholder="0.00" value="${item.gas_cost || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-parking-cost-${claimId}">Parking Cost</label>
                                <input type="number" step="0.01" id="form-parking-cost-${claimId}" placeholder="0.00" value="${item.parking_cost || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-toll-cost-${claimId}">Toll Cost</label>
                                <input type="number" step="0.01" id="form-toll-cost-${claimId}" placeholder="0.00" value="${item.toll_cost || ''}" oninput="triggerLivePreview()">
                            </div>
                            <div class="form-group">
                                <label for="form-linked-rental-${claimId}">Linked Rental Claim ID</label>
                                <input type="text" id="form-linked-rental-${claimId}" placeholder="e.g. ext-12345" value="${item.linked_rental_claim_id || ''}" oninput="triggerLivePreview()">
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-section-card" style="margin-top: 1.25rem; margin-bottom: 0; border: 1px solid rgba(255,255,255,0.05); background: rgba(255,255,255,0.01); padding: 1.25rem;">
                        <div class="form-section-title" style="font-size: 0.9rem; padding-bottom: 0.5rem; margin-bottom: 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.05); color: var(--text-muted);">
                            <span class="section-icon">📂</span> Supporting Documents
                        </div>
                        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem;">
                            Upload supporting documents specifically for this line item.
                        </p>
                        <div class="upload-grid" id="portal-upload-grid-${claimId}">
                            <!-- Populated dynamically -->
                        </div>
                    </div>
                `;
                
                container.appendChild(card);
                renderPortalUploadGridForClaim(claimId);
            });
        }

        let previewTimeout = null;
        function triggerLivePreview() {
            clearTimeout(previewTimeout);
            previewTimeout = setTimeout(async () => {
                syncLineItemsFromDOM();
                
                const activeItems = lineItems.filter(item => item.category);
                if (activeItems.length === 0) {
                    resetCompliancePreviewUI();
                    return;
                }
                
                try {
                    const previewPromises = activeItems.map(async (item) => {
                        const payload = {
                            company_id: "demo_company",
                            employee_email: document.getElementById("form-employee-email").value,
                            employee_name: document.getElementById("form-employee-name").value,
                            department: document.getElementById("form-department").value,
                            manager_email: document.getElementById("form-manager-email").value,
                            
                            claim_id: item.claimId,
                            category: item.category,
                            amount: item.amount,
                            currency: item.currency,
                            expense_date: item.expenseDate,
                            vendor: item.vendor,
                            description: item.description,
                            
                            travel_start_date: item.travel_start_date,
                            travel_end_date: item.travel_end_date,
                            city: item.city,
                            state: item.state,
                            country: item.country,
                            claimed_meals: item.claimed_meals,
                            claimed_lodging: item.claimed_lodging,
                            claimed_incidentals: item.claimed_incidentals,
                            check_in_date: item.check_in_date,
                            check_out_date: item.check_out_date,
                            
                            transportation_type: item.transportation_type,
                            trip_date: item.trip_date,
                            start_location_label: item.start_location_label,
                            start_address: item.start_address,
                            destination_location_label: item.destination_location_label,
                            destination_address: item.destination_address,
                            trip_type: item.trip_type,
                            business_miles: item.business_miles,
                            employee_entered_miles: item.employee_entered_miles,
                            rental_start_date: item.rental_start_date,
                            rental_end_date: item.rental_end_date,
                            rental_cost: item.rental_cost,
                            gas_cost: item.gas_cost,
                            parking_cost: item.parking_cost,
                            toll_cost: item.toll_cost,
                            linked_rental_claim_id: item.linked_rental_claim_id
                        };
                        
                        const response = await fetch("/api/employee/claims/preview", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify(payload)
                        });
                        
                        if (!response.ok) return null;
                        const res = await response.json();
                        return { item, res };
                    });
                    
                    const results = await Promise.all(previewPromises);
                    
                    let totalReimbursable = 0;
                    let totalNonReimbursable = 0;
                    let anyOverage = false;
                    let anyException = false;
                    let anyManagerRequired = false;
                    let aggregatedWarnings = [];
                    let aggregatedChecklist = [];
                    
                    results.forEach((result) => {
                        if (!result) return;
                        const { item, res } = result;
                        const lineNum = lineItems.indexOf(item) + 1;
                        
                        totalReimbursable += safeNumber(res.estimated_reimbursable);
                        totalNonReimbursable += safeNumber(res.estimated_non_reimbursable);
                        
                        if (res.policy_status && (res.policy_status.includes("Exceeds") || res.estimated_non_reimbursable > 0)) {
                            anyOverage = true;
                        }
                        if (!res.is_valid) {
                            anyException = true;
                        }
                        if (res.manager_approval_required) {
                            anyManagerRequired = true;
                        }
                        
                        if (res.warnings && res.warnings.length > 0) {
                            res.warnings.forEach(w => {
                                aggregatedWarnings.push(`Line ${lineNum}: ${w}`);
                            });
                        }
                        
                        const reqDocs = res.required_documents || [];
                        const missDocs = res.missing_documents || [];
                        reqDocs.forEach(doc => {
                            const isMissing = missDocs.includes(doc);
                            aggregatedChecklist.push({
                                lineNum,
                                doc,
                                isMissing
                            });
                        });
                    });
                    
                    const statusEl = document.getElementById("preview-policy-status");
                    if (statusEl) {
                        if (anyException) {
                            statusEl.textContent = "Policy Exception";
                            statusEl.className = "preview-metric-value danger";
                        } else if (anyOverage) {
                            statusEl.textContent = "Approved with Overage";
                            statusEl.className = "preview-metric-value danger";
                        } else {
                            statusEl.textContent = "Approved";
                            statusEl.className = "preview-metric-value success";
                        }
                    }
                    
                    const overageEl = document.getElementById("preview-overage-status");
                    if (overageEl) {
                        if (anyOverage) {
                            overageEl.textContent = "Overage Detected";
                            overageEl.className = "preview-metric-value danger";
                        } else {
                            overageEl.textContent = "Within Limits";
                            overageEl.className = "preview-metric-value success";
                        }
                    }
                    
                    const reimbEl = document.getElementById("preview-reimbursable");
                    if (reimbEl) reimbEl.textContent = formatMoney(totalReimbursable);
                    
                    const nonReimbEl = document.getElementById("preview-non-reimbursable");
                    if (nonReimbEl) nonReimbEl.textContent = formatMoney(totalNonReimbursable);
                    
                    const reviewReqEl = document.getElementById("preview-manager-required");
                    if (reviewReqEl) {
                        reviewReqEl.textContent = anyManagerRequired ? "Yes" : "No";
                        reviewReqEl.className = "preview-metric-value " + (anyManagerRequired ? "danger" : "success");
                    }
                    
                    const warningsContainer = document.getElementById("preview-warnings-container");
                    if (warningsContainer) {
                        warningsContainer.innerHTML = "";
                        if (aggregatedWarnings.length > 0) {
                            aggregatedWarnings.forEach(w => {
                                const banner = document.createElement("div");
                                banner.className = "warning-banner danger";
                                banner.innerHTML = `<span>⚠️</span><span>${escapeHtml(w)}</span>`;
                                warningsContainer.appendChild(banner);
                            });
                        } else {
                            const banner = document.createElement("div");
                            banner.className = "warning-banner info";
                            banner.innerHTML = `<span>ℹ️</span><span>Claim is within standard operational boundaries.</span>`;
                            warningsContainer.appendChild(banner);
                        }
                    }
                    
                    const checklistContainer = document.getElementById("preview-docs-checklist");
                    if (checklistContainer) {
                        checklistContainer.innerHTML = "";
                        if (aggregatedChecklist.length === 0) {
                            checklistContainer.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">No documents required.</div>`;
                        } else {
                            aggregatedChecklist.forEach(item => {
                                const icon = item.isMissing ? "✕" : "✓";
                                const color = item.isMissing ? "#fb7185" : "#34d399";
                                const div = document.createElement("div");
                                div.style = `display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; color: ${color}; font-weight: 500;`;
                                div.innerHTML = `<span>${icon}</span> <span>[Line ${item.lineNum}] ${escapeHtml(item.doc.replace(/_/g, ' ').toUpperCase())}</span>`;
                                checklistContainer.appendChild(div);
                            });
                        }
                    }
                    
                } catch (err) {
                    console.error("Aggregation live preview error", err);
                }
            }, 300);
        }

        function resetCompliancePreviewUI() {
            const statusEl = document.getElementById("preview-policy-status");
            if (statusEl) {
                statusEl.textContent = "N/A";
                statusEl.className = "preview-metric-value";
            }
            const overageEl = document.getElementById("preview-overage-status");
            if (overageEl) {
                overageEl.textContent = "Within Limits";
                overageEl.className = "preview-metric-value success";
            }
            const reimbEl = document.getElementById("preview-reimbursable");
            if (reimbEl) reimbEl.textContent = "$0.00";
            const nonReimbEl = document.getElementById("preview-non-reimbursable");
            if (nonReimbEl) nonReimbEl.textContent = "$0.00";
            const reviewReqEl = document.getElementById("preview-manager-required");
            if (reviewReqEl) {
                reviewReqEl.textContent = "No";
                reviewReqEl.className = "preview-metric-value success";
            }
            const warningsContainer = document.getElementById("preview-warnings-container");
            if (warningsContainer) {
                warningsContainer.innerHTML = `
                    <div class="warning-banner info">
                        <span>ℹ️</span><span>Enter category and details to see live policy evaluation.</span>
                    </div>
                `;
            }
            const checklistContainer = document.getElementById("preview-docs-checklist");
            if (checklistContainer) {
                checklistContainer.innerHTML = `
                    <div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">No category selected.</div>
                `;
            }
        }

        async function submitClaimForm(event) {
            event.preventDefault();
            syncLineItemsFromDOM();
            
            const reportPayload = {
                company_id: "demo_company",
                employee_email: document.getElementById("form-employee-email").value,
                employee_name: document.getElementById("form-employee-name").value,
                department: document.getElementById("form-department").value,
                manager_email: document.getElementById("form-manager-email").value,
                report_title: document.getElementById("form-report-title").value,
                report_period_start: document.getElementById("form-report-start-date").value,
                report_period_end: document.getElementById("form-report-end-date").value
            };
            
            try {
                // 1. Create Report Draft
                const reportResponse = await fetch("/api/reports", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(reportPayload)
                });
                if (!reportResponse.ok) {
                    const errData = await reportResponse.json();
                    throw new Error("Report creation failed: " + (errData.detail || "Unknown error"));
                }
                const reportResult = await reportResponse.json();
                const reportId = reportResult.report_id;
                
                // 2. Add each claim to report
                for (const item of lineItems) {
                    const claimPayload = {
                        claim_id: item.claimId,
                        category: item.category,
                        amount: item.amount,
                        currency: item.currency || "USD",
                        expense_date: item.expenseDate,
                        vendor: item.vendor,
                        business_purpose: document.getElementById("form-business-purpose").value,
                        description: item.description || "",
                        
                        travel_start_date: item.travel_start_date || reportPayload.report_period_start,
                        travel_end_date: item.travel_end_date || reportPayload.report_period_end,
                        city: item.city || "",
                        state: item.state || "",
                        country: item.country || "US",
                        claimed_meals: item.claimed_meals || "0.00",
                        claimed_lodging: item.claimed_lodging || "0.00",
                        claimed_incidentals: item.claimed_incidentals || "0.00",
                        check_in_date: item.check_in_date || null,
                        check_out_date: item.check_out_date || null,
                        
                        transportation_type: item.transportation_type || null,
                        trip_date: item.trip_date || null,
                        start_location_label: item.start_location_label || "",
                        start_address: item.start_address || "",
                        destination_location_label: item.destination_location_label || "",
                        destination_address: item.destination_address || "",
                        trip_type: item.trip_type || "one_way",
                        business_miles: item.business_miles || "0.0",
                        employee_entered_miles: item.employee_entered_miles || "0.0",
                        rental_start_date: item.rental_start_date || null,
                        rental_end_date: item.rental_end_date || null,
                        rental_cost: item.rental_cost || "0.00",
                        gas_cost: item.gas_cost || "0.00",
                        parking_cost: item.parking_cost || "0.00",
                        toll_cost: item.toll_cost || "0.00",
                        linked_rental_claim_id: item.linked_rental_claim_id || null
                    };
                    
                    const claimResponse = await fetch(`/api/reports/${reportId}/claims`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(claimPayload)
                    });
                    if (!claimResponse.ok) {
                        const errData = await claimResponse.json();
                        throw new Error("Failed to add line item: " + (errData.detail || "Unknown error"));
                    }
                }
                
                // 3. Finalize/Submit Report
                const submitResponse = await fetch(`/api/reports/${reportId}/submit`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ override_missing_docs: false })
                });
                if (!submitResponse.ok) {
                    const errData = await submitResponse.json();
                    throw new Error("Report submission failed: " + (errData.detail || "Unknown error"));
                }
                
                showToast("Expense report submitted successfully!", "success");
                resetSubmissionForm();
                switchTab('history');
                
            } catch (err) {
                console.error("Submission failed", err);
                showToast("Submission failed: " + err.message, "error");
            }
        }

        function resetSubmissionForm() {
            const form = document.getElementById("claim-submit-form");
            if (form) form.reset();
            
            const companyIdEl = document.getElementById("form-company-id");
            if (companyIdEl) companyIdEl.value = "demo_company";
            
            const emailEl = document.getElementById("form-employee-email");
            if (emailEl) emailEl.value = USER_EMAIL;
            
            const nameEl = document.getElementById("form-employee-name");
            if (nameEl) nameEl.value = titleCase(USER_EMAIL.split("@")[0]);
            
            const deptEl = document.getElementById("form-department");
            if (deptEl) deptEl.value = "Engineering";
            
            const mgrEl = document.getElementById("form-manager-email");
            if (mgrEl) mgrEl.value = "manager@company.com";
            
            const startDateEl = document.getElementById("form-report-start-date");
            if (startDateEl) startDateEl.value = new Date().toISOString().substring(0, 10);
            
            const endDateEl = document.getElementById("form-report-end-date");
            if (endDateEl) endDateEl.value = new Date().toISOString().substring(0, 10);
            
            lineItems = [createDefaultLineItem()];
            lineItemDocs = {};
            
            renderLineItems();
            updateOverallRunningTotal();
            resetCompliancePreviewUI();
            
            const demoContainer = document.getElementById("demo-claimant-container");
            if (demoContainer) {
                if (USER_ROLE === "finance_admin") {
                    demoContainer.style.display = "block";
                } else {
                    demoContainer.style.display = "none";
                }
            }
        }

        function useDemoClaimant(email) {
            if (!email) return;
            resetSubmissionForm();
            
            document.getElementById("form-employee-email").value = email;
            document.getElementById("form-employee-name").value = titleCase(email.split("@")[0]);
            
            const selectEl = document.getElementById("form-demo-select");
            if (selectEl) selectEl.value = email;
            
            const claimId = lineItems[0].claimId;
            
            if (email === "fresh.manager.test@company.com") {
                document.getElementById("form-employee-name").value = "Fresh Manager Test";
                document.getElementById("form-department").value = "Operations";
                document.getElementById("form-manager-email").value = "obamigbade@gmail.com";
                
                document.getElementById("form-report-title").value = "Operations site visit";
                document.getElementById("form-report-start-date").value = "2026-05-10";
                document.getElementById("form-report-end-date").value = "2026-05-12";
                document.getElementById("form-business-purpose").value = "Operations site visit";
                
                document.getElementById(`form-category-${claimId}`).value = "meals";
                handleLineItemCategoryChange(claimId, "meals");
                document.getElementById(`form-amount-${claimId}`).value = "150.00";
                document.getElementById(`form-claimed-meals-${claimId}`).value = "150.00";
                document.getElementById(`form-travel-start-${claimId}`).value = "2026-05-10";
                document.getElementById(`form-travel-end-${claimId}`).value = "2026-05-12";
                document.getElementById(`form-city-${claimId}`).value = "Chicago";
                document.getElementById(`form-state-${claimId}`).value = "IL";
                document.getElementById(`form-description-${claimId}`).value = "Operations review with local team.";
                document.getElementById(`form-vendor-${claimId}`).value = "Operations Team Meal";
            } else if (email === "receipt.test@company.com") {
                document.getElementById("form-employee-name").value = "Receipt Test";
                document.getElementById("form-department").value = "Finance";
                document.getElementById("form-manager-email").value = "obamigbade@gmail.com";
                
                document.getElementById("form-report-title").value = "Finance audit and planning";
                document.getElementById("form-report-start-date").value = "2026-05-15";
                document.getElementById("form-report-end-date").value = "2026-05-17";
                document.getElementById("form-business-purpose").value = "Finance audit and planning";
                
                document.getElementById(`form-category-${claimId}`).value = "meals";
                handleLineItemCategoryChange(claimId, "meals");
                document.getElementById(`form-amount-${claimId}`).value = "250.00";
                document.getElementById(`form-claimed-meals-${claimId}`).value = "250.00";
                document.getElementById(`form-travel-start-${claimId}`).value = "2026-05-15";
                document.getElementById(`form-travel-end-${claimId}`).value = "2026-05-17";
                document.getElementById(`form-city-${claimId}`).value = "Austin";
                document.getElementById(`form-state-${claimId}`).value = "TX";
                document.getElementById(`form-description-${claimId}`).value = "Annual finance planning session.";
                document.getElementById(`form-vendor-${claimId}`).value = "Finance Audit Dinner";
            } else if (email === "auth.hotel.docs.test@company.com") {
                document.getElementById("form-employee-name").value = "Auth Hotel Docs Test";
                document.getElementById("form-department").value = "Sales";
                document.getElementById("form-manager-email").value = "obamigbade@gmail.com";
                
                document.getElementById("form-report-title").value = "Annual Sales Kickoff";
                document.getElementById("form-report-start-date").value = "2026-05-20";
                document.getElementById("form-report-end-date").value = "2026-05-23";
                document.getElementById("form-business-purpose").value = "Annual Sales Kickoff";
                
                document.getElementById(`form-category-${claimId}`).value = "lodging";
                handleLineItemCategoryChange(claimId, "lodging");
                document.getElementById(`form-amount-${claimId}`).value = "600.00";
                document.getElementById(`form-claimed-lodging-${claimId}`).value = "600.00";
                document.getElementById(`form-travel-start-${claimId}`).value = "2026-05-20";
                document.getElementById(`form-travel-end-${claimId}`).value = "2026-05-23";
                document.getElementById(`form-city-${claimId}`).value = "San Francisco";
                document.getElementById(`form-state-${claimId}`).value = "CA";
                document.getElementById(`form-check-in-${claimId}`).value = "2026-05-20";
                document.getElementById(`form-check-out-${claimId}`).value = "2026-05-23";
                document.getElementById(`form-description-${claimId}`).value = "Sales presentation and customer meetings.";
                document.getElementById(`form-vendor-${claimId}`).value = "SF Hotel";
            } else if (email === "auth.flight.docs.test@company.com") {
                document.getElementById("form-employee-name").value = "Auth Flight Docs Test";
                document.getElementById("form-department").value = "Travel";
                document.getElementById("form-manager-email").value = "obamigbade@gmail.com";
                
                document.getElementById("form-report-title").value = "Technical integration";
                document.getElementById("form-report-start-date").value = "2026-05-25";
                document.getElementById("form-report-end-date").value = "2026-05-28";
                document.getElementById("form-business-purpose").value = "Technical integration";
                
                document.getElementById(`form-category-${claimId}`).value = "flight";
                handleLineItemCategoryChange(claimId, "flight");
                document.getElementById(`form-amount-${claimId}`).value = "850.00";
                document.getElementById(`form-travel-start-${claimId}`).value = "2026-05-25";
                document.getElementById(`form-travel-end-${claimId}`).value = "2026-05-28";
                document.getElementById(`form-city-${claimId}`).value = "Seattle";
                document.getElementById(`form-state-${claimId}`).value = "WA";
                document.getElementById(`form-description-${claimId}`).value = "Integration kickoff with cloud engineering.";
                document.getElementById(`form-vendor-${claimId}`).value = "Cloud Airways";
            } else if (email === "auth.rejection.test@company.com") {
                document.getElementById("form-employee-name").value = "Auth Rejection Test";
                document.getElementById("form-department").value = "Compliance";
                document.getElementById("form-manager-email").value = "obamigbade@gmail.com";
                
                document.getElementById("form-report-title").value = "Compliance workshop";
                document.getElementById("form-report-start-date").value = "2026-06-01";
                document.getElementById("form-report-end-date").value = "2026-06-03";
                document.getElementById("form-business-purpose").value = "Compliance workshop";
                
                document.getElementById(`form-category-${claimId}`).value = "meals";
                handleLineItemCategoryChange(claimId, "meals");
                document.getElementById(`form-amount-${claimId}`).value = "400.00";
                document.getElementById(`form-claimed-meals-${claimId}`).value = "400.00";
                document.getElementById(`form-travel-start-${claimId}`).value = "2026-06-01";
                document.getElementById(`form-travel-end-${claimId}`).value = "2026-06-03";
                document.getElementById(`form-city-${claimId}`).value = "Miami";
                document.getElementById(`form-state-${claimId}`).value = "FL";
                document.getElementById(`form-description-${claimId}`).value = "Southeastern regional compliance review.";
                document.getElementById(`form-vendor-${claimId}`).value = "Compliance Dinner";
            } else if (email === "employee.portal.meals@company.com") {
                document.getElementById("form-report-title").value = "Business meetings in New York";
                document.getElementById("form-report-start-date").value = "2026-04-12";
                document.getElementById("form-report-end-date").value = "2026-04-14";
                document.getElementById("form-business-purpose").value = "Business meetings in New York";
                
                document.getElementById(`form-category-${claimId}`).value = "meals";
                handleLineItemCategoryChange(claimId, "meals");
                document.getElementById(`form-amount-${claimId}`).value = "300.00";
                document.getElementById(`form-claimed-meals-${claimId}`).value = "300.00";
                document.getElementById(`form-travel-start-${claimId}`).value = "2026-04-12";
                document.getElementById(`form-travel-end-${claimId}`).value = "2026-04-14";
                document.getElementById(`form-city-${claimId}`).value = "New York";
                document.getElementById(`form-state-${claimId}`).value = "NY";
                document.getElementById(`form-description-${claimId}`).value = "Employee meals within per diem test claim.";
                document.getElementById(`form-vendor-${claimId}`).value = "NYC Diners";
            } else if (email === "employee.portal.meals.over@company.com") {
                document.getElementById("form-report-title").value = "Business meetings in New York";
                document.getElementById("form-report-start-date").value = "2026-04-12";
                document.getElementById("form-report-end-date").value = "2026-04-14";
                document.getElementById("form-business-purpose").value = "Business meetings in New York";
                
                document.getElementById(`form-category-${claimId}`).value = "meals";
                handleLineItemCategoryChange(claimId, "meals");
                document.getElementById(`form-amount-${claimId}`).value = "450.00";
                document.getElementById(`form-claimed-meals-${claimId}`).value = "450.00";
                document.getElementById(`form-travel-start-${claimId}`).value = "2026-04-12";
                document.getElementById(`form-travel-end-${claimId}`).value = "2026-04-14";
                document.getElementById(`form-city-${claimId}`).value = "New York";
                document.getElementById(`form-state-${claimId}`).value = "NY";
                document.getElementById(`form-description-${claimId}`).value = "Employee meals exceeding per diem test claim.";
                document.getElementById(`form-vendor-${claimId}`).value = "Five Star Bistro";
            } else if (email === "employee.portal.mileage@company.com") {
                document.getElementById("form-report-title").value = "Same-day client meeting";
                document.getElementById("form-report-start-date").value = "2026-04-12";
                document.getElementById("form-report-end-date").value = "2026-04-12";
                document.getElementById("form-business-purpose").value = "Same-day client meeting";
                
                document.getElementById(`form-category-${claimId}`).value = "transportation";
                handleLineItemCategoryChange(claimId, "transportation");
                document.getElementById(`form-trans-type-${claimId}`).value = "personal_vehicle";
                
                document.getElementById(`form-amount-${claimId}`).value = "0.00";
                document.getElementById(`form-trip-date-${claimId}`).value = "2026-04-12";
                document.getElementById(`form-start-loc-${claimId}`).value = "home";
                document.getElementById(`form-start-addr-${claimId}`).value = "Raleigh, NC";
                document.getElementById(`form-dest-loc-${claimId}`).value = "client_site";
                document.getElementById(`form-dest-addr-${claimId}`).value = "Charlotte, NC";
                document.getElementById(`form-trip-type-${claimId}`).value = "round_trip";
                document.getElementById(`form-biz-miles-${claimId}`).value = "280";
                document.getElementById(`form-entered-miles-${claimId}`).value = "280";
                document.getElementById(`form-description-${claimId}`).value = "Employee mileage test claim.";
                document.getElementById(`form-vendor-${claimId}`).value = "Personal Vehicle Mileage";
            } else if (email === "employee.portal.rental@company.com") {
                document.getElementById("form-report-title").value = "Business conference travel";
                document.getElementById("form-report-start-date").value = "2026-04-12";
                document.getElementById("form-report-end-date").value = "2026-04-14";
                document.getElementById("form-business-purpose").value = "Business conference travel";
                
                document.getElementById(`form-category-${claimId}`).value = "transportation";
                handleLineItemCategoryChange(claimId, "transportation");
                document.getElementById(`form-trans-type-${claimId}`).value = "rental_car";
                
                document.getElementById(`form-amount-${claimId}`).value = "320.00";
                document.getElementById(`form-rental-cost-${claimId}`).value = "320.00";
                document.getElementById(`form-rental-start-${claimId}`).value = "2026-04-12";
                document.getElementById(`form-rental-end-${claimId}`).value = "2026-04-14";
                document.getElementById(`form-description-${claimId}`).value = "Employee rental car test claim.";
                document.getElementById(`form-vendor-${claimId}`).value = "Enterprise Rent-A-Car";
            } else if (email === "employee.portal.flight@company.com") {
                document.getElementById("form-report-title").value = "Client conference flight";
                document.getElementById("form-report-start-date").value = "2026-07-02";
                document.getElementById("form-report-end-date").value = "2026-07-02";
                document.getElementById("form-business-purpose").value = "Client conference flight";
                
                document.getElementById(`form-category-${claimId}`).value = "flight";
                handleLineItemCategoryChange(claimId, "flight");
                document.getElementById(`form-amount-${claimId}`).value = "1350.00";
                document.getElementById(`form-description-${claimId}`).value = "Employee flight ticket test claim.";
                document.getElementById(`form-vendor-${claimId}`).value = "Delta Airlines";
            }
            
            updateOverallRunningTotal();
            triggerLivePreview();
        }

        async function showClaimDetails(claimId) {
            toggleModal(true);
            const body = document.querySelector(".modal-body");
            const title = document.querySelector(".modal-header h2");
            const sub = document.getElementById("modal-session-id");
            
            title.textContent = "Claim Detail & Audit Timeline";
            sub.textContent = `Claim ID: ${claimId}`;
            
            body.innerHTML = `
                <div style="text-align: center; padding: 4rem 2rem; color: var(--text-muted);">
                    <div class="spinner" style="margin: 0 auto 1rem auto; width: 24px; height: 24px;"></div>
                    Fetching complete claim profile...
                </div>
            `;
            
            try {
                const response = await fetch(`/api/employee/claims/${claimId}`);
                if (!response.ok) throw new Error("Failed to load details");
                
                const data = await response.json();
                const exp = data.expense;
                const docs = data.documents || [];
                const decisions = data.decisions || [];
                const audits = data.audit_logs || [];
                
                title.textContent = `Claim: ${escapeHtml(titleCase(exp.category || "Expense"))}`;
                
                let statusBg, statusColor, statusText;
                switch (exp.status) {
                    case 'approved':
                    case 'auto_approved':
                        statusBg = 'rgba(16, 185, 129, 0.15)';
                        statusColor = '#34d399';
                        statusText = exp.status === 'auto_approved' ? 'Auto-Approved (AI)' : 'Approved (Manager)';
                        break;
                    case 'rejected':
                        statusBg = 'rgba(244, 63, 94, 0.15)';
                        statusColor = '#fb7185';
                        statusText = 'Rejected';
                        break;
                    case 'blocked_missing_docs':
                        statusBg = 'rgba(239, 68, 68, 0.15)';
                        statusColor = '#f87171';
                        statusText = 'Blocked (Missing Docs)';
                        break;
                    case 'pending_review':
                    default:
                        statusBg = 'rgba(245, 158, 11, 0.15)';
                        statusColor = '#f59e0b';
                        statusText = 'Pending Review';
                }
                
                const docUrls = {};
                docs.forEach(d => {
                    docUrls[d.doc_type] = d.gcs_path ? `/api/document/${claimId}/${d.doc_type}` : null;
                });
                
                const isTravel = ["meals", "lodging", "flight"].includes(exp.category);
                const isTransport = ["transportation", "rental_car", "rental_car_gas", "parking", "tolls"].includes(exp.category);
                
                body.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                        <div style="background: ${statusBg}; color: ${statusColor}; border: 1px solid ${statusColor}40; padding: 1rem; border-radius: 12px; display: flex; align-items: center; gap: 0.75rem;">
                            <span style="font-size: 1.5rem; line-height: 1;">🛡️</span>
                            <div>
                                <h4 style="font-size: 0.95rem; font-weight: 700; margin: 0; color: white;">${statusText}</h4>
                                <p style="font-size: 0.8rem; margin: 0.2rem 0 0 0; color: rgba(255,255,255,0.7);">${escapeHtml(exp.policy_status || "Compliance evaluation completed.")}</p>
                            </div>
                        </div>

                        <div class="review-details-card" style="margin-top: 0; padding: 1.5rem; width: auto; background: rgba(255,255,255,0.02); border: 1px solid var(--glass-border); border-radius: 16px;">
                            <h4 style="font-size: 0.85rem; margin-bottom: 1rem; color: #a5b4fc; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.4rem; font-weight: 700;">Claim Summary</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; font-size: 0.82rem;">
                                <div class="review-field"><span>Employee</span><strong>${escapeHtml(exp.employee_name)}</strong></div>
                                <div class="review-field"><span>Email</span><strong style="font-size: 0.75rem; font-weight: 500; word-break: break-all;">${escapeHtml(exp.employee_email)}</strong></div>
                                <div class="review-field"><span>Amount</span><strong style="color: #34d399; font-size: 1.05rem;">${formatMoney(exp.amount)} (${escapeHtml(exp.currency || "USD")})</strong></div>
                                <div class="review-field"><span>Department</span><strong>${escapeHtml(exp.department || "N/A")}</strong></div>
                                <div class="review-field"><span>Manager</span><strong>${escapeHtml(exp.manager_email || "N/A")}</strong></div>
                                <div class="review-field"><span>Expense Date</span><strong>${escapeHtml(exp.expense_date || "N/A")}</strong></div>
                                <div class="review-field" style="grid-column: 1 / -1;"><span>Business Purpose</span><strong>${escapeHtml(exp.business_purpose || "N/A")}</strong></div>
                                ${exp.description ? `<div class="review-field" style="grid-column: 1 / -1;"><span>Description</span><strong style="font-style: italic; font-weight: 400; color: var(--text-muted);">"${escapeHtml(exp.description)}"</strong></div>` : ''}
                            </div>
                        </div>

                        ${isTravel ? `
                        <div style="background: rgba(99, 102, 241, 0.03); border: 1px solid rgba(99, 102, 241, 0.1); padding: 1.2rem; border-radius: 14px;">
                            <h4 style="font-size: 0.85rem; text-transform: uppercase; color: #a5b4fc; letter-spacing: 0.05em; margin-bottom: 0.8rem; font-weight: 700;">📅 Travel Metrics</h4>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem;">
                                <div><strong style="color: var(--text-muted);">Dates:</strong> ${escapeHtml(exp.travel_start_date || "N/A")} to ${escapeHtml(exp.travel_end_date || "N/A")}</div>
                                <div><strong style="color: var(--text-muted);">Destination:</strong> ${escapeHtml(exp.city || "N/A")}, ${escapeHtml(exp.state || "N/A")}</div>
                                <div><strong style="color: var(--text-muted);">Claimed Meals:</strong> ${formatMoney(exp.claimed_meals)}</div>
                                <div><strong style="color: var(--text-muted);">Claimed Lodging:</strong> ${formatMoney(exp.claimed_lodging)}</div>
                            </div>
                        </div>
                        ` : ''}

                        ${isTransport ? `
                        <div style="background: rgba(139, 92, 246, 0.03); border: 1px solid rgba(139, 92, 246, 0.1); padding: 1.2rem; border-radius: 14px;">
                            <h4 style="font-size: 0.85rem; text-transform: uppercase; color: #c084fc; letter-spacing: 0.05em; margin-bottom: 0.8rem; font-weight: 700;">🚗 Transportation Metrics</h4>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem;">
                                <div><strong style="color: var(--text-muted);">Type:</strong> ${escapeHtml(exp.transportation_type || "N/A")}</div>
                                <div><strong style="color: var(--text-muted);">Route:</strong> ${escapeHtml(exp.start_address || "N/A")} ➔ ${escapeHtml(exp.destination_address || "N/A")}</div>
                                ${exp.business_miles ? `<div><strong style="color: var(--text-muted);">Miles:</strong> ${exp.business_miles} mi</div>` : ''}
                                ${exp.rental_cost ? `<div><strong style="color: var(--text-muted);">Rental Cost:</strong> ${formatMoney(exp.rental_cost)}</div>` : ''}
                                ${exp.gas_cost ? `<div><strong style="color: var(--text-muted);">Gas Cost:</strong> ${formatMoney(exp.gas_cost)}</div>` : ''}
                                ${exp.parking_cost ? `<div><strong style="color: var(--text-muted);">Parking Cost:</strong> ${formatMoney(exp.parking_cost)}</div>` : ''}
                            </div>
                        </div>
                        ` : ''}

                        <div class="document-verification-box" style="padding: 1.25rem; border-radius: 14px; background: rgba(255, 255, 255, 0.01); border: 1px solid rgba(255, 255, 255, 0.05);">
                            <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin-bottom: 0.8rem; font-weight: 700;">📂 Document Checklist & Action</h4>
                            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                ${(() => {
                                    const required = exp.required_documents || [];
                                    const missing = exp.missing_documents || [];
                                    if (required.length === 0) {
                                        return `<div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">No specific documents required.</div>`;
                                    }
                                    return required.map(docType => {
                                        const isMissing = missing.includes(docType);
                                        const url = docUrls[docType];
                                        const label = DOC_TYPES[docType] ? DOC_TYPES[docType].label : docType.replace(/_/g, ' ').toUpperCase();
                                        return `
                                            <div class="doc-row" style="display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 0.8rem; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 10px; gap: 0.5rem;">
                                                <div style="display: flex; flex-direction: column;">
                                                    <span style="font-size: 0.85rem; font-weight: 600; color: white;">${label}</span>
                                                    <span style="font-size: 0.75rem; color: ${url ? '#10b981' : '#fb7185'}; font-weight: 500;">
                                                        ${url ? '✓ Uploaded' : '✕ Missing'}
                                                    </span>
                                                </div>
                                                <div style="display: flex; gap: 0.4rem; align-items: center;">
                                                    ${url ? `
                                                    <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; flex: none; text-decoration: none;">
                                                        View
                                                    </a>
                                                    ` : ''}
                                                    <label class="btn-doc-upload" id="upload-btn-${claimId}-${docType}" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; background: rgba(255,255,255,0.05); border: 1px solid var(--glass-border); color: var(--text-main); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.2rem; transition: var(--transition); user-select: none;">
                                                        <input type="file" onchange="uploadModalDoc('${claimId}', '${docType}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display: none;">
                                                        <span>${url ? 'Replace' : 'Upload'}</span>
                                                    </label>
                                                </div>
                                            </div>
                                        `;
                                    }).join('');
                                })()}
                            </div>
                        </div>

                        <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 1.25rem;">
                            <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin-bottom: 1rem; font-weight: 700; display: flex; align-items: center; gap: 0.4rem;">
                                📜 Audit History Timeline
                            </h4>
                            <div style="display: flex; flex-direction: column; gap: 0.8rem; padding-left: 0.5rem; border-left: 2px dashed rgba(255,255,255,0.1); margin-left: 0.5rem;">
                                ${audits.map(audit => {
                                    const eventDate = audit.timestamp ? new Date(audit.timestamp).toLocaleString() : "N/A";
                                    return `
                                        <div style="position: relative; padding-left: 1rem; font-size: 0.8rem;">
                                            <div style="position: absolute; left: -1.35rem; top: 0.2rem; width: 8px; height: 8px; border-radius: 50%; background: var(--primary); box-shadow: 0 0 6px var(--primary);"></div>
                                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.15rem;">
                                                <strong style="color: white;">${escapeHtml(audit.event_type.replace(/_/g, ' ').toUpperCase())}</strong>
                                                <span style="color: var(--text-muted); font-size: 0.72rem;">${eventDate}</span>
                                            </div>
                                            <p style="margin: 0; color: rgba(255,255,255,0.85);">${escapeHtml(audit.event_message)}</p>
                                            <p style="margin: 0.15rem 0 0 0; color: var(--text-muted); font-size: 0.72rem;">
                                                Actor: <span style="color: #c7d2fe; font-weight: 500;">${escapeHtml(audit.actor_email || audit.actor || "N/A")}</span> (${escapeHtml(audit.actor_role || "N/A")})
                                            </p>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                `;
            } catch (err) {
                console.error("Failed to fetch claim profile", err);
                body.innerHTML = `
                    <div style="text-align: center; padding: 4rem 2rem; color: #fb7185;">
                        <span style="font-size: 2.5rem;">✕</span>
                        <h3 style="margin-top: 1rem; color: white;">Error Loading Profile</h3>
                        <p style="font-size: 0.85rem; margin-top: 0.2rem;">${err.message}</p>
                    </div>
                `;
            }
        }

        async function uploadModalDoc(claimId, docType, inputElement) {
            if (!inputElement.files || inputElement.files.length === 0) return;
            const file = inputElement.files[0];
            
            const btn = document.getElementById(`upload-btn-${claimId}-${docType}`);
            const originalHTML = btn.innerHTML;
            if (btn) {
                btn.style.pointerEvents = "none";
                btn.innerHTML = `<div class="spinner" style="width:12px; height:12px; border-width:1.5px; margin:0; display:inline-block; vertical-align:middle;"></div>`;
            }
            
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const response = await fetch(`/api/employee/claims/${claimId}/documents/${docType}`, {
                    method: "POST",
                    body: formData
                });
                
                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "Upload failed");
                }
                
                showToast(`${file.name} uploaded successfully!`, "success");
                await showClaimDetails(claimId);
                
                if (USER_ROLE === "employee") {
                    fetchExpenseHistory();
                } else {
                    fetchPendingApprovals();
                    fetchExpenseHistory();
                }
            } catch (err) {
                console.error("Modal document upload failed", err);
                showToast("Upload failed: " + err.message, "error");
                if (btn) {
                    btn.innerHTML = originalHTML;
                    btn.style.pointerEvents = "all";
                }
            }
        }

        function switchTab(tab) {
            document.querySelectorAll(".tab-section").forEach(sec => sec.style.display = "none");
            document.querySelectorAll(".tab-btn").forEach(btn => {
                btn.classList.remove("active");
                btn.style.color = "var(--text-muted)";
                btn.style.borderBottom = "none";
            });
            
            const activeBtn = document.getElementById(`tab-${tab === 'audit-trail' ? 'audit' : tab}`);
            if (activeBtn) {
                activeBtn.classList.add("active");
                activeBtn.style.color = "white";
            }

            if (tab === 'pending') {
                document.getElementById("section-pending").style.display = "block";
                fetchPendingApprovals();
            } else if (tab === 'history') {
                document.getElementById("section-history").style.display = "block";
                fetchExpenseHistory();
            } else if (tab === 'audit-trail') {
                document.getElementById("section-audit-trail").style.display = "block";
            } else if (tab === 'submit') {
                document.getElementById("section-submit").style.display = "block";
                initSubmitForm();
            } else if (tab === 'cards') {
                document.getElementById("section-cards").style.display = "block";
                fetchCardTransactions();
            }
        }

        function getStatusBadgeHTML(status) {
            let bg, color, text;
            switch(status) {
                case 'submitted':
                    bg = 'rgba(255, 255, 255, 0.05)';
                    color = '#cbd5e1';
                    text = 'Submitted';
                    break;
                case 'pending_review':
                    bg = 'rgba(245, 158, 11, 0.1)';
                    color = '#f59e0b';
                    text = 'Pending Review';
                    break;
                case 'approved':
                    bg = 'rgba(16, 185, 129, 0.1)';
                    color = '#10b981';
                    text = 'Approved';
                    break;
                case 'auto_approved':
                    bg = 'rgba(16, 185, 129, 0.15)';
                    color = '#34d399';
                    text = 'Auto-Approved';
                    break;
                case 'rejected':
                    bg = 'rgba(244, 63, 94, 0.1)';
                    color = '#fb7185';
                    text = 'Rejected';
                    break;
                case 'blocked_missing_docs':
                    bg = 'rgba(239, 68, 68, 0.1)';
                    color = '#f87171';
                    text = 'Blocked (Docs)';
                    break;
                default:
                    bg = 'rgba(255, 255, 255, 0.05)';
                    color = '#cbd5e1';
                    text = status;
            }
            return `<span style="background: ${bg}; color: ${color}; border: 1px solid ${color}33; padding: 0.25rem 0.5rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; display: inline-block;">${text}</span>`;
        }

        // --- SQL-Style Custom Query Builder Helpers ---
        function addQueryCondition(field = 'employee_name', operator = 'contains', value1 = '', value2 = '') {
            const container = document.getElementById("query-conditions-container");
            if (!container) return;
            
            const rowId = ++queryRowCounter;
            const row = document.createElement("div");
            row.id = `query-rule-row-${rowId}`;
            row.className = "query-rule-row";
            row.style.display = "flex";
            row.style.gap = "0.75rem";
            row.style.alignItems = "center";
            row.style.flexWrap = "wrap";
            row.style.background = "rgba(255, 255, 255, 0.02)";
            row.style.border = "1px solid rgba(255, 255, 255, 0.05)";
            row.style.padding = "0.75rem 1rem";
            row.style.borderRadius = "10px";
            row.style.transition = "background-color 0.2s";
            
            row.innerHTML = `
                <select class="query-field-select form-group" onchange="onQueryFieldChange(${rowId})" style="background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.4rem 0.6rem; color: white; font-family: inherit; font-size: 0.85rem; outline: none; cursor: pointer; min-width: 150px;">
                    <option value="employee_name" ${field === 'employee_name' ? 'selected' : ''}>Employee Name</option>
                    <option value="department" ${field === 'department' ? 'selected' : ''}>Department</option>
                    <option value="category" ${field === 'category' ? 'selected' : ''}>Expense Type</option>
                    <option value="amount" ${field === 'amount' ? 'selected' : ''}>Amount</option>
                    <option value="status" ${field === 'status' ? 'selected' : ''}>Report Status</option>
                    <option value="status" ${field === 'status' ? 'selected' : ''}>Approval Status</option>
                    <option value="created_at" ${field === 'created_at' ? 'selected' : ''}>Date Submitted</option>
                    <option value="updated_at" ${field === 'updated_at' ? 'selected' : ''}>Date Changed</option>
                </select>
                
                <select class="query-operator-select form-group" onchange="onQueryOperatorChange(${rowId})" style="background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.4rem 0.6rem; color: white; font-family: inherit; font-size: 0.85rem; outline: none; cursor: pointer; min-width: 130px;">
                    <!-- Populated dynamically by onQueryFieldChange -->
                </select>
                
                <div class="query-value-container" style="display: flex; gap: 0.5rem; align-items: center; flex-grow: 1;">
                    <!-- Populated dynamically -->
                </div>
                
                <button onclick="removeQueryCondition(${rowId})" style="background: rgba(244, 63, 94, 0.1); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.2); border-radius: 8px; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 1.1rem; transition: var(--transition); line-height: 1; border-color: rgba(244, 63, 94, 0.25);">
                    &times;
                </button>
            `;
            
            container.appendChild(row);
            onQueryFieldChange(rowId, operator, value1, value2);
            updateMatchingCount();
        }

        function onQueryFieldChange(rowId, targetOperator = null, value1 = '', value2 = '') {
            const row = document.getElementById(`query-rule-row-${rowId}`);
            if (!row) return;
            
            const fieldSelect = row.querySelector(".query-field-select");
            const opSelect = row.querySelector(".query-operator-select");
            const field = fieldSelect.value;
            
            let opHTML = "";
            let defaultOp = "equals";
            
            if (field === 'created_at' || field === 'updated_at') {
                opHTML = `
                    <option value="equals">Equals</option>
                    <option value="contains">Contains</option>
                    <option value="before">Before</option>
                    <option value="after">After</option>
                    <option value="between">Between</option>
                    <option value="within_days">Within Last</option>
                `;
                defaultOp = targetOperator || "within_days";
            } else if (field === 'amount') {
                opHTML = `
                    <option value="equals">Equals</option>
                    <option value="greater_than">Greater Than</option>
                    <option value="less_than">Less Than</option>
                    <option value="between">Between</option>
                `;
                defaultOp = targetOperator || "greater_than";
            } else if (field === 'status') {
                opHTML = `
                    <option value="equals">Equals</option>
                    <option value="contains">Contains</option>
                `;
                defaultOp = targetOperator || "equals";
            } else { // employee_name, department, category
                opHTML = `
                    <option value="contains">Contains</option>
                    <option value="equals">Equals</option>
                `;
                defaultOp = targetOperator || "contains";
            }
            
            opSelect.innerHTML = opHTML;
            opSelect.value = defaultOp;
            
            onQueryOperatorChange(rowId, value1, value2);
        }

        function onQueryOperatorChange(rowId, value1 = '', value2 = '') {
            const row = document.getElementById(`query-rule-row-${rowId}`);
            if (!row) return;
            
            const field = row.querySelector(".query-field-select").value;
            const operator = row.querySelector(".query-operator-select").value;
            const valueContainer = row.querySelector(".query-value-container");
            
            let valHTML = "";
            
            if (operator === 'between') {
                if (field === 'created_at' || field === 'updated_at') {
                    valHTML = `
                        <input type="date" class="query-val-1" value="${value1}" style="background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.4rem 0.6rem; color: white; font-family: inherit; font-size: 0.85rem; outline: none; width: 140px;">
                        <span style="color: var(--text-muted); font-size: 0.8rem;">to</span>
                        <input type="date" class="query-val-2" value="${value2}" style="background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.4rem 0.6rem; color: white; font-family: inherit; font-size: 0.85rem; outline: none; width: 140px;">
                    `;
                } else if (field === 'amount') {
                    valHTML = `
                        <input type="number" step="0.01" class="query-val-1" placeholder="Min" value="${value1}" style="background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.4rem 0.6rem; color: white; font-family: inherit; font-size: 0.85rem; outline: none; width: 100px;">
                        <span style="color: var(--text-muted); font-size: 0.8rem;">and</span>
                        <input type="number" step="0.01" class="query-val-2" placeholder="Max" value="${value2}" style="background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.4rem 0.6rem; color: white; font-family: inherit; font-size: 0.85rem; outline: none; width: 100px;">
                    `;
                }
            } else if (operator === 'within_days') {
                valHTML = `
                    <select class="query-val-1" style="background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.4rem 0.6rem; color: white; font-family: inherit; font-size: 0.85rem; outline: none; cursor: pointer; width: 140px;">
                        <option value="30" ${value1 == '30' ? 'selected' : ''}>30 Days</option>
                        <option value="60" ${value1 == '60' ? 'selected' : ''}>60 Days</option>
                        <option value="90" ${value1 == '90' ? 'selected' : ''}>90 Days</option>
                        <option value="180" ${value1 == '180' ? 'selected' : ''}>180 Days</option>
                    </select>
                `;
            } else if (field === 'status') {
                valHTML = `
                    <select class="query-val-1" style="background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.4rem 0.6rem; color: white; font-family: inherit; font-size: 0.85rem; outline: none; cursor: pointer; width: 160px;">
                        <option value="pending" ${value1 === 'pending' ? 'selected' : ''}>Pending Manager Approval</option>
                        <option value="approved_all" ${value1 === 'approved_all' ? 'selected' : ''}>Approved reports</option>
                        <option value="rejected" ${value1 === 'rejected' ? 'selected' : ''}>Rejected reports</option>
                        <option value="submitted" ${value1 === 'submitted' ? 'selected' : ''}>Submitted</option>
                        <option value="pending_review" ${value1 === 'pending_review' ? 'selected' : ''}>Pending Review</option>
                        <option value="approved" ${value1 === 'approved' ? 'selected' : ''}>Approved</option>
                        <option value="auto_approved" ${value1 === 'auto_approved' ? 'selected' : ''}>Auto-Approved</option>
                    </select>
                `;
            } else if (field === 'category') {
                valHTML = `
                    <select class="query-val-1" style="background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.4rem 0.6rem; color: white; font-family: inherit; font-size: 0.85rem; outline: none; cursor: pointer; width: 160px;">
                        <option value="meals" ${value1 === 'meals' ? 'selected' : ''}>Meals</option>
                        <option value="lodging" ${value1 === 'lodging' ? 'selected' : ''}>Lodging</option>
                        <option value="travel" ${value1 === 'travel' ? 'selected' : ''}>Travel / Flight</option>
                        <option value="hotel" ${value1 === 'hotel' ? 'selected' : ''}>Hotel</option>
                        <option value="mileage" ${value1 === 'mileage' ? 'selected' : ''}>Mileage / Gas</option>
                        <option value="parking" ${value1 === 'parking' ? 'selected' : ''}>Parking</option>
                        <option value="office" ${value1 === 'office' ? 'selected' : ''}>Office / Supplies</option>
                        <option value="other" ${value1 === 'other' ? 'selected' : ''}>Other</option>
                    </select>
                `;
            } else {
                const isDate = (field === 'created_at' || field === 'updated_at');
                const isNumber = (field === 'amount');
                valHTML = `<input type="${isDate ? 'date' : (isNumber ? 'number' : 'text')}" class="query-val-1" value="${value1}" placeholder="Value..." style="background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 8px; padding: 0.4rem 0.6rem; color: white; font-family: inherit; font-size: 0.85rem; outline: none; flex-grow: 1;">`;
            }
            
            valueContainer.innerHTML = valHTML;
            
            const inputs = valueContainer.querySelectorAll("input, select");
            inputs.forEach(input => {
                input.addEventListener("change", updateMatchingCount);
                input.addEventListener("input", updateMatchingCount);
            });
        }

        function removeQueryCondition(rowId) {
            const row = document.getElementById(`query-rule-row-${rowId}`);
            if (row) row.remove();
            updateMatchingCount();
        }

        function clearQueryBuilder() {
            const container = document.getElementById("query-conditions-container");
            if (container) container.innerHTML = "";
            addQueryCondition('employee_name', 'contains', '');
        }

        function applyPresetQuery(presetType) {
            const container = document.getElementById("query-conditions-container");
            if (!container) return;
            
            container.innerHTML = "";
            
            if (presetType === 'all') {
                // Keep empty
            } else if (presetType === 'pending_last_30') {
                addQueryCondition('status', 'equals', 'pending');
                addQueryCondition('created_at', 'within_days', '30');
            } else if (presetType === 'approved_last_60') {
                addQueryCondition('status', 'equals', 'approved_all');
                addQueryCondition('updated_at', 'within_days', '60');
            } else if (presetType === 'rejected') {
                addQueryCondition('status', 'equals', 'rejected');
            } else if (presetType === 'high_value_pending') {
                addQueryCondition('status', 'equals', 'pending');
                addQueryCondition('amount', 'greater_than', '500');
            }
            
            applyQueryBuilder();
        }

        function getFilteredExpenses() {
            if (!allExpenses || allExpenses.length === 0) return [];
            
            const rows = document.querySelectorAll("#query-conditions-container .query-rule-row");
            if (rows.length === 0) return allExpenses;
            
            const rules = [];
            rows.forEach(row => {
                const field = row.querySelector(".query-field-select").value;
                const operator = row.querySelector(".query-operator-select").value;
                const val1El = row.querySelector(".query-val-1");
                const val2El = row.querySelector(".query-val-2");
                
                const val1 = val1El ? val1El.value : "";
                const val2 = val2El ? val2El.value : "";
                
                rules.push({ field, operator, val1, val2 });
            });
            
            return allExpenses.filter(exp => {
                for (const rule of rules) {
                    let recordVal = exp[rule.field];
                    
                    if (rule.field === 'updated_at') {
                        recordVal = exp.updated_at || exp.created_at;
                    }
                    
                    if (rule.field === 'created_at' || rule.field === 'updated_at') {
                        if (!recordVal) return false;
                        const recordDate = new Date(recordVal);
                        
                        if (rule.operator === 'within_days') {
                            const diffDays = (Date.now() - recordDate.getTime()) / (1000 * 60 * 60 * 24);
                            const limitDays = parseFloat(rule.val1);
                            if (isNaN(limitDays) || diffDays > limitDays || diffDays < 0) return false;
                        } else if (rule.operator === 'before' || rule.operator === 'less_than') {
                            if (!rule.val1) continue;
                            const limitDate = new Date(rule.val1);
                            if (recordDate >= limitDate) return false;
                        } else if (rule.operator === 'after' || rule.operator === 'greater_than') {
                            if (!rule.val1) continue;
                            const limitDate = new Date(rule.val1);
                            if (recordDate <= limitDate) return false;
                        } else if (rule.operator === 'between') {
                            if (!rule.val1 || !rule.val2) continue;
                            const limitDate1 = new Date(rule.val1);
                            const limitDate2 = new Date(rule.val2);
                            if (recordDate < limitDate1 || recordDate > limitDate2) return false;
                        } else if (rule.operator === 'equals') {
                            if (!rule.val1) continue;
                            const limitDate = new Date(rule.val1);
                            if (recordDate.toDateString() !== limitDate.toDateString()) return false;
                        } else if (rule.operator === 'contains') {
                            if (!rule.val1) continue;
                            const dStr = recordDate.toLocaleString().toLowerCase();
                            const rStr = String(recordVal || "").toLowerCase();
                            const target = String(rule.val1).toLowerCase();
                            if (!dStr.includes(target) && !rStr.includes(target)) return false;
                        }
                    } else if (rule.field === 'amount') {
                        const amount = parseFloat(recordVal || 0);
                        const v1 = parseFloat(rule.val1 || 0);
                        const v2 = parseFloat(rule.val2 || 0);
                        
                        if (rule.operator === 'equals') {
                            if (amount !== v1) return false;
                        } else if (rule.operator === 'greater_than') {
                            if (amount <= v1) return false;
                        } else if (rule.operator === 'less_than') {
                            if (amount >= v1) return false;
                        } else if (rule.operator === 'between') {
                            if (amount < v1 || amount > v2) return false;
                        }
                    } else if (rule.field === 'status') {
                        const status = (recordVal || "").toLowerCase();
                        const target = (rule.val1 || "").toLowerCase();
                        
                        if (target === 'pending') {
                            if (status !== 'pending_review' && status !== 'submitted') return false;
                        } else if (target === 'approved_all') {
                            if (status !== 'approved' && status !== 'auto_approved') return false;
                        } else if (target === 'rejected') {
                            if (status !== 'rejected') return false;
                        } else {
                            if (rule.operator === 'equals') {
                                if (status !== target) return false;
                            } else {
                                if (!status.includes(target)) return false;
                            }
                        }
                    } else {
                        const strVal = String(recordVal || "").toLowerCase();
                        const target = String(rule.val1 || "").toLowerCase();
                        
                        if (rule.operator === 'equals') {
                            if (strVal !== target) return false;
                        } else {
                            if (!strVal.includes(target)) return false;
                        }
                    }
                }
                return true;
            });
        }

        function updateMatchingCount() {
            const container = document.getElementById("query-conditions-container");
            const label = document.getElementById("query-builder-matching-count");
            if (!container || !label) return;
            
            const matches = getFilteredExpenses();
            label.innerHTML = `Matching: <span style="color: white; font-weight: 700;">${matches.length}</span> records`;
        }

        function applyQueryBuilder() {
            const filtered = getFilteredExpenses();
            renderExpenseHistoryTable(filtered);
            updateMatchingCount();
        }

        function renderExpenseHistoryTable(expenses) {
            const tbody = document.getElementById("history-table-body");
            if (!tbody) return;

            if (!expenses || expenses.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" style="padding: 4rem; text-align: center; color: var(--text-muted);">
                            <span style="font-size: 2rem;">📭</span>
                            <h4 style="margin-top: 1rem; color: white;">No Expenses Found</h4>
                            <p style="font-size: 0.85rem; margin-top: 0.2rem;">Expenses will appear here once ingested via Pub/Sub or initialized on the dashboard.</p>
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = "";
            expenses.forEach(exp => {
                try {
                    const statusBadge = getStatusBadgeHTML(exp.status);
                    const policyColor = exp.policy_status && exp.policy_status.includes("Within policy") ? "#10b981" : "#fb7185";
                    
                    const decisionText = exp.status === 'approved' ? 'Approved (Manager)' : (exp.status === 'auto_approved' ? 'Auto-Approved (AI)' : (exp.status === 'rejected' ? 'Rejected' : 'Pending'));
                    const decisionColor = exp.status === 'approved' || exp.status === 'auto_approved' ? '#10b981' : (exp.status === 'rejected' ? '#ef4444' : '#f59e0b');
                    
                    const formattedDate = exp.created_at ? new Date(exp.created_at).toLocaleString() : "N/A";
                    
                    const tr = document.createElement("tr");
                    tr.style.borderBottom = "1px solid rgba(255,255,255,0.04)";
                    tr.style.transition = "background-color 0.2s";
                    tr.onmouseenter = () => tr.style.backgroundColor = "rgba(255,255,255,0.02)";
                    tr.onmouseleave = () => tr.style.backgroundColor = "transparent";
                    
                    const reviewerText = exp.reviewer_email || exp.decision_by_email || "N/A";
                    const reviewerRole = exp.reviewer_role || exp.decision_by_role || "";
                    
                    tr.innerHTML = `
                        <td style="padding: 1rem 0.75rem;"><span style="background: rgba(255,255,255,0.06); padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.75rem; text-transform: uppercase;">${escapeHtml(exp.category || "N/A")}</span></td>
                        <td style="padding: 1rem 0.75rem; color: var(--text-muted); font-size: 0.8rem;">${formattedDate}</td>
                        <td style="padding: 1rem 0.75rem;">
                            <div style="font-weight: 500; color: white;">${escapeHtml(exp.employee_name || "N/A")}</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(exp.employee_email || "")}</div>
                        </td>
                        <td style="padding: 1rem 0.75rem;"><span style="color: #cbd5e1; font-weight: 500;">${escapeHtml(exp.department || "N/A")}</span></td>
                        <td style="padding: 1rem 0.75rem; color: #cbd5e1; font-size: 0.8rem;">${escapeHtml(exp.manager_email || "N/A")}</td>
                        <td style="padding: 1rem 0.75rem;">
                            <div style="font-weight: 500; color: #cbd5e1; font-size: 0.8rem;">${escapeHtml(exp.submitted_by_email || "System")}</div>
                            <div style="font-size: 0.7rem; color: #a5b4fc; font-weight: 500;">Role: ${escapeHtml(exp.submitted_by_role || "user")}</div>
                        </td>
                        <td style="padding: 1rem 0.75rem; font-weight: 700; color: white;">${formatMoney(exp.amount)}</td>
                        <td style="padding: 1rem 0.75rem;">
                            <div style="margin-bottom: 0.25rem;">${statusBadge}</div>
                            <div style="color: ${policyColor}; font-size: 0.75rem; font-weight: 600;">${escapeHtml(exp.policy_status || "N/A")}</div>
                        </td>
                        <td style="padding: 1rem 0.75rem;">
                            ${exp.reviewer_email || exp.decision_by_email ? `
                                <div style="font-weight: 500; color: #cbd5e1; font-size: 0.8rem;">${escapeHtml(reviewerText)}</div>
                                <div style="font-size: 0.7rem; color: #f472b6; font-weight: 500;">Role: ${escapeHtml(reviewerRole)}</div>
                            ` : `
                                <span style="color: var(--text-muted); font-style: italic; font-size: 0.8rem;">No review</span>
                            `}
                        </td>
                        <td style="padding: 1rem 0.75rem; text-align: right;">
                            <div style="display: flex; gap: 0.5rem; justify-content: flex-end; align-items: center;">
                                <button class="btn btn-receipt" onclick="showClaimDetails('${exp.claim_id}')" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto; background: rgba(99,102,241,0.1); color: #cbd5e1; border-color: rgba(99,102,241,0.25);">
                                    View Details
                                </button>
                                ${(USER_ROLE === 'finance_admin' || USER_ROLE === 'manager') ? `
                                <button class="btn btn-receipt" onclick="loadAuditTrail('${exp.claim_id}', '${escapeHtml(exp.employee_name)}', '${exp.amount || 0}')" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; display: inline-flex; height: auto;">
                                    View Trail
                                </button>
                                ` : ''}
                            </div>
                        </td>
                    `;
                    tbody.appendChild(tr);
                } catch (err) {
                    console.warn("Failed to render history expense:", exp ? exp.claim_id : "unknown", err);
                }
            });
        }

        async function fetchExpenseHistory(force = false) {
            const tbody = document.getElementById("history-table-body");
            try {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" style="padding: 3rem; text-align: center; color: var(--text-muted);">
                            <div class="spinner" style="margin: 0 auto 1rem auto; width: 24px; height: 24px;"></div>
                            Syncing database and loading history...
                        </td>
                    </tr>
                `;
                
                let apiPath = USER_ROLE === 'employee' ? '/api/employee/claims' : '/api/expenses';
                if (force && apiPath === '/api/expenses') {
                    apiPath += "?refresh=true";
                }
                const response = await fetch(apiPath);
                if (!response.ok) throw new Error("HTTP " + response.status);
                
                const expenses = await response.json();
                allExpenses = expenses;

                const qbPanel = document.getElementById("query-builder-panel");
                if (qbPanel && (USER_ROLE === "manager" || USER_ROLE === "finance_admin")) {
                    qbPanel.style.display = "block";
                    const condContainer = document.getElementById("query-conditions-container");
                    if (condContainer && condContainer.children.length === 0) {
                        clearQueryBuilder();
                    }
                } else if (qbPanel) {
                    qbPanel.style.display = "none";
                }

                applyQueryBuilder();
                
                // Show/hide export buttons based on USER_ROLE
                const showExports = (USER_ROLE === "manager" || USER_ROLE === "finance_admin");
                const btnExpensesCsv = document.getElementById("btn-export-expenses-csv");
                const btnExpensesExcel = document.getElementById("btn-export-expenses-excel");
                const btnAuditCsv = document.getElementById("btn-export-audit-csv");
                const btnAuditExcel = document.getElementById("btn-export-audit-excel");

                if (showExports) {
                    if (btnExpensesCsv) btnExpensesCsv.style.display = "inline-block";
                    if (btnExpensesExcel) btnExpensesExcel.style.display = "inline-block";
                    if (btnAuditCsv) btnAuditCsv.style.display = "inline-block";
                    if (btnAuditExcel) btnAuditExcel.style.display = "inline-block";
                } else {
                    if (btnExpensesCsv) btnExpensesCsv.style.display = "none";
                    if (btnExpensesExcel) btnExpensesExcel.style.display = "none";
                    if (btnAuditCsv) btnAuditCsv.style.display = "none";
                    if (btnAuditExcel) btnAuditExcel.style.display = "none";
                }
                
            } catch (err) {
                console.error("Failed to load history", err);
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" style="padding: 3rem; text-align: center; color: #fb7185;">
                            ❌ Failed to load history: ${err.message}
                        </td>
                    </tr>
                `;
            }
        }

        async function exportExpensesData(format) {
            const filtered = getFilteredExpenses();
            if (!filtered || filtered.length === 0) {
                showToast("No records available to export.", "error");
                return;
            }
            
            const claimIds = filtered.map(c => c.claim_id).filter(Boolean);
            try {
                showToast("Generating expenses export...", "success");
                const response = await fetch(`/api/export/expenses/${format}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ claim_ids: claimIds })
                });
                
                if (!response.ok) {
                    const errText = await response.text();
                    throw new Error(errText || `HTTP ${response.status}`);
                }
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `expenses_export_${new Date().toISOString().split('T')[0]}.${format === 'csv' ? 'csv' : 'xlsx'}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                showToast("Expenses export downloaded successfully!", "success");
            } catch (err) {
                console.error("Export failed", err);
                showToast("Export failed: " + err.message, "error");
            }
        }
        
        async function exportAuditData(format) {
            const filtered = getFilteredExpenses();
            if (!filtered || filtered.length === 0) {
                showToast("No records available to export audit trail.", "error");
                return;
            }
            
            const claimIds = filtered.map(c => c.claim_id).filter(Boolean);
            try {
                showToast("Generating audit trail export...", "success");
                const response = await fetch(`/api/export/audit/${format}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ claim_ids: claimIds })
                });
                
                if (!response.ok) {
                    const errText = await response.text();
                    throw new Error(errText || `HTTP ${response.status}`);
                }
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `audit_export_${new Date().toISOString().split('T')[0]}.${format === 'csv' ? 'csv' : 'xlsx'}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                showToast("Audit trail export downloaded successfully!", "success");
            } catch (err) {
                console.error("Audit export failed", err);
                showToast("Export failed: " + err.message, "error");
            }
        }

        window.exportExpensesData = exportExpensesData;
        window.exportAuditData = exportAuditData;


        async function loadAuditTrail(claimId, employeeName, amount) {
            switchTab('audit-trail');
            const container = document.getElementById("audit-trail-container");
            container.innerHTML = `
                <div style="text-align: center; padding: 4rem 2rem; color: var(--text-muted);">
                    <div class="spinner" style="margin: 0 auto 1rem auto; width: 24px; height: 24px;"></div>
                    Fetching audit timeline and claim details...
                </div>
            `;
            
            try {
                const response = await fetch(`/api/expenses/${claimId}`);
                if (!response.ok) throw new Error("HTTP " + response.status);
                
                const data = await response.json();
                const exp = data.expense || {};
                const logs = data.audit_logs || [];
                
                let headerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div>
                            <h3 style="font-size: 1.25rem; font-weight: 700; color: white;">Audit Trail for ${escapeHtml(exp.employee_name || employeeName)}</h3>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">Claim ID: ${escapeHtml(claimId)}</p>
                        </div>
                        <div style="font-size: 1.35rem; font-weight: 800; color: white;">${formatMoney(exp.amount || amount)}</div>
                    </div>
                `;

                // Beautiful glassmorphic Summary Card
                let summaryHTML = `
                    <div class="audit-summary-card" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1); backdrop-filter: blur(5px);">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.2rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 0.8rem;">
                            <div>
                                <span style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 700; letter-spacing: 0.05em;">Claim Lifecycle Summary</span>
                                <h3 style="font-size: 1.15rem; font-weight: 700; color: white; margin-top: 2px;">Details</h3>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 1.25rem; font-weight: 800; color: #818cf8;">${formatMoney(exp.amount || amount)}</div>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">Amount</span>
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem 1.5rem; font-size: 0.85rem;">
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Employee</strong>
                                <span style="color: white; font-weight: 600;">${escapeHtml(exp.employee_name || employeeName)}</span>
                                <span style="display: block; color: var(--text-muted); font-size: 0.8rem;">${escapeHtml(exp.employee_email || "N/A")}</span>
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Assigned Manager</strong>
                                <span style="color: white; font-weight: 600;">${escapeHtml(exp.manager_email || "N/A")}</span>
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Department</strong>
                                <span style="color: #cbd5e1; font-weight: 500;">${escapeHtml(exp.department || "N/A")}</span>
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Submitted By</strong>
                                <span style="color: white; font-weight: 600;">${escapeHtml(exp.submitted_by_email || "System")}</span>
                                <span style="display: block; color: #a5b4fc; font-size: 0.75rem; font-weight: 500;">Role: ${escapeHtml(exp.submitted_by_role || "user")}</span>
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Reviewer / Decision By</strong>
                                ${exp.reviewer_email || exp.decision_by_email ? `
                                    <span style="color: white; font-weight: 600;">${escapeHtml(exp.reviewer_email || exp.decision_by_email)}</span>
                                    <span style="display: block; color: #f472b6; font-size: 0.75rem; font-weight: 500;">Role: ${escapeHtml(exp.reviewer_role || exp.decision_by_role || "manager")}</span>
                                ` : `
                                    <span style="color: var(--text-muted); font-style: italic;">No manager review yet</span>
                                `}
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); display: block; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.2rem;">Reimbursement Status</strong>
                                <span style="margin-top: 0.15rem; display: inline-block;">${getStatusBadgeHTML(exp.status)}</span>
                            </div>
                        </div>
                    </div>
                `;
                
                if (logs.length === 0) {
                    container.innerHTML = headerHTML + summaryHTML + `
                        <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
                            📭 No audit events registered for this claim.
                        </div>
                    `;
                    return;
                }
                
                let timelineHTML = `<div style="position: relative; padding-left: 2.5rem; margin-top: 1rem;">`;
                timelineHTML += `<div style="position: absolute; left: 0.7rem; top: 1rem; bottom: 1rem; width: 2px; background: rgba(255,255,255,0.1);"></div>`;
                
                logs.forEach((log, idx) => {
                    const formattedTime = log.timestamp ? new Date(log.timestamp).toLocaleString() : "N/A";
                    
                    let dotColor = "var(--primary)";
                    let dotIcon = "○";
                    if (log.event_type === 'claim_ingested') { dotColor = "#3b82f6"; dotIcon = "📥"; }
                    else if (log.event_type === 'employee_submitted_claim') { dotColor = "#10b981"; dotIcon = "📝"; }
                    else if (log.event_type === 'session_bound') { dotColor = "#8b5cf6"; dotIcon = "🔗"; }
                    else if (log.event_type === 'document_uploaded') { dotColor = "#10b981"; dotIcon = "📂"; }
                    else if (log.event_type === 'policies_reevaluated') { dotColor = "#6366f1"; dotIcon = "🛡️"; }
                    else if (log.event_type === 'manager_decision') { dotColor = "#f59e0b"; dotIcon = "✍️"; }
                    else if (log.event_type === 'agent_finalized') { dotColor = "#10b981"; dotIcon = "🏁"; }
                    
                    const isSecureAuth = log.authenticated === true || (log.metadata && log.metadata.authenticated === true);
                    
                    let changeDetailsHTML = "";
                    let actionTaken = "";
                    let fieldChanged = "";
                    let prevVal = "";
                    let newVal = "";

                    if (log.event_type === 'claim_created_from_session' || log.event_type === 'claim_ingested' || log.event_type === 'employee_submitted_claim') {
                        actionTaken = "Initial Claim Creation";
                        fieldChanged = "Record Status";
                        prevVal = "N/A (New Record)";
                        newVal = log.event_message || "Claim created";
                    } else if (log.event_type === 'session_bound') {
                        actionTaken = "Vertex AI Agent Bind Session";
                        fieldChanged = "Session ID";
                        prevVal = "None";
                        newVal = log.session_id || "Active session";
                    } else if (log.event_type === 'document_uploaded') {
                        actionTaken = "Document Attachment";
                        fieldChanged = "Required Documents";
                        const docType = log.event_message ? (log.event_message.split("document ")[1]?.split(":")[0] || "receipt") : "receipt";
                        prevVal = "Missing " + docType;
                        newVal = "Attached: " + (log.metadata?.gcs_path ? log.metadata.gcs_path.split("/").pop() : "File uploaded");
                    } else if (log.event_type === 'policies_reevaluated') {
                        actionTaken = "Policy Compliance Check";
                        fieldChanged = "policy_status";
                        prevVal = "Unchecked / Pending Docs";
                        newVal = log.metadata?.policy_review?.status || "Within policy";
                    } else if (log.event_type === 'manager_decision') {
                        actionTaken = log.event_message && log.event_message.includes("override") ? "Finance Admin Override" : "Manager Review Decision";
                        fieldChanged = "status";
                        prevVal = "pending_review";
                        newVal = log.event_message && log.event_message.includes("approved") ? "approved" : "rejected";
                    } else if (log.event_type === 'agent_finalized') {
                        actionTaken = "AI Compliance Agent Finalization";
                        fieldChanged = "status";
                        prevVal = "pending_review";
                        newVal = log.event_message && log.event_message.includes("auto_approved") ? "auto_approved" : "approved";
                    }

                    if (actionTaken) {
                        changeDetailsHTML = `
                            <div class="audit-change-details" style="margin-top: 0.8rem; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 0.75rem 1rem; border-radius: 10px; font-size: 0.825rem; display: flex; flex-direction: column; gap: 0.4rem; max-width: 500px;">
                                <div style="display: flex; justify-content: space-between;"><span style="color: var(--text-muted); font-weight: 600;">Action Taken:</span><span style="color: white; font-weight: 700;">${escapeHtml(actionTaken)}</span></div>
                                <div style="display: flex; justify-content: space-between;"><span style="color: var(--text-muted);">Field Changed:</span><span style="color: #a5b4fc; font-weight: 600; font-family: monospace;">${escapeHtml(fieldChanged)}</span></div>
                                <div style="display: flex; justify-content: space-between;"><span style="color: var(--text-muted);">Previous Value:</span><span style="color: #fb7185; text-decoration: line-through; max-width: 60%; word-break: break-all; text-align: right;">${escapeHtml(String(prevVal))}</span></div>
                                <div style="display: flex; justify-content: space-between;"><span style="color: var(--text-muted);">New Value:</span><span style="color: #34d399; font-weight: 600; max-width: 60%; word-break: break-all; text-align: right;">${escapeHtml(String(newVal))}</span></div>
                            </div>
                        `;
                    }
                    
                    timelineHTML += `
                        <div style="position: relative; margin-bottom: 2rem;">
                            <div style="position: absolute; left: -2.5rem; top: 0.1rem; width: 1.5rem; height: 1.5rem; border-radius: 50%; background: #0c0e24; border: 2px solid ${dotColor}; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; z-index: 2; box-shadow: 0 0 10px ${dotColor}33;">
                                ${dotIcon}
                            </div>
                            
                            <div>
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <h4 style="font-size: 1rem; font-weight: 600; color: white;">${escapeHtml(log.event_type.replace(/_/g, ' ').toUpperCase())}</h4>
                                    <span style="font-size: 0.75rem; color: var(--text-muted);">${formattedTime}</span>
                                </div>
                                <p style="font-size: 0.9rem; color: var(--text-muted); margin-top: 0.3rem;">${escapeHtml(log.event_message)}</p>
                                ${(() => {
                                    if (log.actor_email) {
                                        const displayRole = (log.actor_role || "").replace(/_/g, ' ').toUpperCase();
                                        const authLabel = isSecureAuth ? `
                                            <div style="display: inline-flex; align-items: center; gap: 0.25rem; font-size: 0.72rem; color: #10b981; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); padding: 0.15rem 0.4rem; border-radius: 6px; font-weight: 600; margin-top: 0.25rem; box-shadow: 0 0 8px rgba(16,185,129,0.15);">
                                                <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                                                    <path fill-rule="evenodd" d="M8.603 3.702A3 3 0 0110.53 2.5h2.94a3 3 0 011.927 1.202l1.696 2.544a1 1 0 00.765.424l3.033.242a3 3 0 012.637 2.637l.242 3.033a1 1 0 00.424.765l2.544 1.696a3 3 0 010 5.156l-2.544 1.696a1 1 0 00-.424.765l-.242 3.033a3 3 0 01-2.637 2.637l-3.033.242a1 1 0 00-.765.424l-1.696 2.544a3 3 0 01-5.156 0l-1.696-2.544a1 1 0 00-.765-.424l-3.033-.242a3 3 0 01-2.637-2.637l-.242-3.033a1 1 0 00-.424-.765L1.202 15.03a3 3 0 010-5.156l2.544-1.696a1 1 0 00.424-.765l.242-3.033a3 3 0 012.637-2.637l3.033-.242a1 1 0 00.765-.424l1.696-2.544zM16.207 10.207a1 1 0 00-1.414-1.414L11 12.586 9.207 10.793a1 1 0 00-1.414 1.414l2.5 2.5a1 1 0 001.414 0l4.5-4.5z" clip-rule="evenodd" />
                                                </svg>
                                                Secure Auth Verified
                                            </div>
                                        ` : `
                                            <span style="font-size: 0.75rem; color: #10b981; font-weight: 600; text-transform: uppercase; margin-top: 0.1rem; display: inline-block;">Auth: Google Authenticated</span>
                                        `;
                                        return `
                                            <span style="font-size: 0.75rem; color: ${dotColor}; font-weight: 600; text-transform: uppercase; margin-top: 0.2rem; display: inline-block;">Actor: ${escapeHtml(log.actor_email)}</span>
                                            <br>
                                            <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; margin-top: 0.1rem; display: inline-block;">Role: ${escapeHtml(displayRole)}</span>
                                            <br>
                                            ${authLabel}
                                        `;
                                    } else if (log.actor_display === 'Legacy Manager' || log.actor === 'manager' || log.actor === 'user' || log.actor === 'Legacy Manager' || log.event_type === 'manager_decision') {
                                        const displayRole = (log.actor_role || "manager").replace(/_/g, ' ').toUpperCase();
                                        const authLabel = isSecureAuth ? `
                                            <div style="display: inline-flex; align-items: center; gap: 0.25rem; font-size: 0.72rem; color: #10b981; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); padding: 0.15rem 0.4rem; border-radius: 6px; font-weight: 600; margin-top: 0.25rem; box-shadow: 0 0 8px rgba(16,185,129,0.15);">
                                                <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                                                    <path fill-rule="evenodd" d="M8.603 3.702A3 3 0 0110.53 2.5h2.94a3 3 0 011.927 1.202l1.696 2.544a1 1 0 00.765.424l3.033.242a3 3 0 012.637 2.637l.242 3.033a1 1 0 00.424.765l2.544 1.696a3 3 0 010 5.156l-2.544 1.696a1 1 0 00-.424.765l-.242 3.033a3 3 0 01-2.637 2.637l-3.033.242a1 1 0 00-.765.424l-1.696 2.544a3 3 0 01-5.156 0l-1.696-2.544a1 1 0 00-.765-.424l-3.033-.242a3 3 0 01-2.637-2.637l-.242-3.033a1 1 0 00-.424-.765L1.202 15.03a3 3 0 010-5.156l2.544-1.696a1 1 0 00.424-.765l.242-3.033a3 3 0 012.637-2.637l3.033-.242a1 1 0 00.765-.424l1.696-2.544zM16.207 10.207a1 1 0 00-1.414-1.414L11 12.586 9.207 10.793a1 1 0 00-1.414 1.414l2.5 2.5a1 1 0 001.414 0l4.5-4.5z" clip-rule="evenodd" />
                                                </svg>
                                                Secure Auth Verified
                                            </div>
                                        ` : `
                                            <span style="font-size: 0.75rem; color: #f59e0b; font-weight: 600; text-transform: uppercase; margin-top: 0.1rem; display: inline-block;">Auth: Pre-Google Auth</span>
                                        `;
                                        return `
                                            <span style="font-size: 0.75rem; color: ${dotColor}; font-weight: 600; text-transform: uppercase; margin-top: 0.2rem; display: inline-block;">Actor: Legacy Manager</span>
                                            <br>
                                            <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; margin-top: 0.1rem; display: inline-block;">Role: ${escapeHtml(displayRole)}</span>
                                            <br>
                                            ${authLabel}
                                        `;
                                    } else {
                                        return `
                                            <span style="font-size: 0.75rem; color: ${dotColor}; font-weight: 600; text-transform: uppercase; margin-top: 0.2rem; display: inline-block;">Actor: ${escapeHtml(log.actor)}</span>
                                        `;
                                    }
                                })()}
                                ${changeDetailsHTML}
                            </div>
                        </div>
                    `;
                });
                
                timelineHTML += `</div>`;
                container.innerHTML = headerHTML + summaryHTML + timelineHTML;
                
            } catch (err) {
                console.error("Failed to load audit trail", err);
                container.innerHTML = `
                    <div style="text-align: center; padding: 3rem; color: #fb7185;">
                        ❌ Failed to load audit trail: ${err.message}
                    </div>
                `;
            }
        }

        function runPolicyCheck(claim) {
            let result = {
                isValid: true,
                category: claim.category || 'N/A',
                nights: null,
                costPerNight: null,
                requiredDocs: [],
                missingDocs: [],
                warnings: [],
                status: 'Within policy'
            };

            const cat = (claim.category || '').toLowerCase();
            const amount = claim.amount || 0;

            // 0. Integrated Per Diem Check
            if (['meals', 'lodging', 'hotel', 'travel'].includes(cat)) {
                if (claim.per_diem_review) {
                    const pdr = claim.per_diem_review;
                    if (pdr.status === "Missing company policy") {
                        result.isValid = false;
                        result.status = "Missing company policy";
                        result.warnings.push(pdr.warning || "Missing company policy");
                    } else if (pdr.status === "Missing per diem data") {
                        result.isValid = false;
                        result.status = "Missing per diem data";
                        result.warnings.push(pdr.warning || "Missing per diem data");
                    } else if (pdr.status === "Exceeds company per diem") {
                        result.isValid = false;
                        result.status = "Exceeds company per diem";
                        result.warnings.push(pdr.warning || "Exceeds company per diem");
                        result.requiredDocs.push("Manager Approval Letter");
                        if (!pdr.manager_letter_uploaded) {
                            result.missingDocs.push("Manager Approval Letter");
                        }
                    } else if (pdr.status === "Requires manager approval") {
                        result.isValid = true;
                        result.status = "Requires manager approval";
                        result.warnings.push(pdr.warning || "Requires manager approval");
                    }
                }
            }

            // 1. Lodging / Hotel Review
            if (cat === 'lodging' || cat === 'hotel') {
                if (claim.check_in_date && claim.check_out_date) {
                    const checkIn = new Date(claim.check_in_date);
                    const checkOut = new Date(claim.check_out_date);
                    const diffTime = Math.abs(checkOut - checkIn);
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    if (diffDays > 0) {
                        result.nights = diffDays;
                        result.costPerNight = amount / diffDays;
                        
                        if (result.costPerNight > 350.0) {
                            result.requiredDocs.push("Manager Approval Letter");
                            if (!claim.manager_approval_letter_url) {
                                result.missingDocs.push("Manager Approval Letter");
                                result.warnings.push("Manager approval letter required because lodging exceeds $350 per night.");
                                result.isValid = false;
                                result.status = "Requires manager approval letter";
                            }
                        }
                    }
                }
            }

            // 2. Flight Ticket Review
            const isFlight = cat === 'flight' || cat === 'airfare' || (cat === 'travel' && (claim.travel_type || '').toLowerCase() === 'flight');
            if (isFlight) {
                result.requiredDocs.push("Flight Ticket Receipt");
                if (!claim.flight_ticket_receipt_url) {
                    result.missingDocs.push("Flight Ticket Receipt");
                    result.warnings.push("Flight ticket receipt required before approval.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }

                if (amount > 1200.0) {
                    result.requiredDocs.push("Manager Approval Letter");
                    if (!claim.manager_approval_letter_url) {
                        result.missingDocs.push("Manager Approval Letter");
                        result.warnings.push("Manager approval letter required because flight ticket exceeds $1200.");
                        result.isValid = false;
                        if (result.status !== "Needs documentation") {
                            result.status = "Requires manager approval letter";
                        }
                    }
                }
            }

            if (!result.isValid && result.status === 'Within policy') {
                result.status = 'Needs documentation';
            }

            // 3. Office Supplies / Printing Supplies
            const officeCats = ["office_supplies", "printing_supplies", "printer_ink", "toner", "paper", "printing_service"];
            if (officeCats.includes(cat)) {
                result.isOffice = true;
                const hasReceipt = !!(claim.office_receipt_url || claim.receipt_url);
                if (amount > 50.0) {
                    result.requiredDocs.push("Receipt");
                    if (!hasReceipt) {
                        result.missingDocs.push("Receipt");
                        result.warnings.push("Receipt is required for office supplies above $50.");
                        result.isValid = false;
                        result.status = "Needs documentation";
                    }
                }
                if (!claim.business_purpose) {
                    result.warnings.push("Business purpose is required for office supplies.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }
                if (amount > 250.0 && result.isValid) {
                    result.status = "Requires manager approval";
                }
            }

            // 4. Business Parking
            const parkingCats = ["business_parking", "parking_fee"];
            if (parkingCats.includes(cat)) {
                result.isParking = true;
                result.requiredDocs.push("Parking Receipt");
                const hasReceipt = !!(claim.parking_receipt_url || claim.receipt_url);
                if (!hasReceipt) {
                    result.missingDocs.push("Parking Receipt");
                    result.warnings.push("Parking receipt is required.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }
                if (!claim.parking_date) {
                    result.warnings.push("Parking date is required.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }
                if (!claim.parking_location) {
                    result.warnings.push("Parking location is required.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }
                if (!claim.business_purpose) {
                    result.warnings.push("Business purpose is required.");
                    result.isValid = false;
                    result.status = "Needs documentation";
                }
                if (result.isValid) {
                    result.status = "Within policy";
                }
            }

            // 5. Parking Tickets / Citations
            const citationCats = ["parking_ticket", "parking_citation"];
            if (citationCats.includes(cat)) {
                result.isCitation = true;
                result.requiredDocs.push("Manager Approval Letter");
                if (!claim.manager_approval_letter_url) {
                    result.missingDocs.push("Manager Approval Letter");
                    result.isValid = false;
                    result.status = "Potentially non-reimbursable";
                    result.warnings.push("Parking fines or citations are normally not reimbursable without explicit manager approval.");
                } else {
                    result.status = "Requires manager approval";
                }
            }

            return result;
        }

        function getDocumentsConfig(claim, policy) {
            const cat = (claim.category || '').toLowerCase();
            const amount = claim.amount || 0;
            const isFlight = cat === 'flight' || cat === 'airfare' || (cat === 'travel' && (claim.travel_type || '').toLowerCase() === 'flight');
            const officeCats = ["office_supplies", "printing_supplies", "printer_ink", "toner", "paper", "printing_service"];
            const isOffice = officeCats.includes(cat);
            const parkingCats = ["business_parking", "parking_fee"];
            const isParking = parkingCats.includes(cat);
            const citationCats = ["parking_ticket", "parking_citation"];
            const isCitation = citationCats.includes(cat);
            const isHotel = cat === 'lodging' || cat === 'hotel';

            let docs = [];

            if (isHotel) {
                docs.push({
                    type: "hotel_receipt",
                    name: "Hotel Receipt",
                    required: false,
                    url: claim.hotel_receipt_url || claim.receipt_url
                });
                docs.push({
                    type: "manager_approval_letter",
                    name: "Manager Approval Letter",
                    required: (policy.costPerNight > 350.0),
                    url: claim.manager_approval_letter_url
                });
            } else if (isFlight) {
                docs.push({
                    type: "flight_ticket_receipt",
                    name: "Flight Ticket Receipt",
                    required: true,
                    url: claim.flight_ticket_receipt_url || claim.receipt_url
                });
                docs.push({
                    type: "manager_approval_letter",
                    name: "Manager Approval Letter",
                    required: (amount > 1200.0),
                    url: claim.manager_approval_letter_url
                });
            } else if (isOffice) {
                docs.push({
                    type: "office_receipt",
                    name: "Office Receipt",
                    required: (amount > 50.0),
                    url: claim.office_receipt_url || claim.receipt_url
                });
            } else if (isParking) {
                docs.push({
                    type: "parking_receipt",
                    name: "Parking Receipt",
                    required: true,
                    url: claim.parking_receipt_url || claim.receipt_url
                });
            } else if (isCitation) {
                docs.push({
                    type: "parking_receipt",
                    name: "Parking Receipt",
                    required: false,
                    url: claim.parking_receipt_url || claim.receipt_url
                });
                docs.push({
                    type: "manager_approval_letter",
                    name: "Manager Approval Letter",
                    required: true,
                    url: claim.manager_approval_letter_url
                });
            } else {
                docs.push({
                    type: "receipt",
                    name: "Receipt",
                    required: (amount > 50.0),
                    url: claim.receipt_url
                });
            }

            // Add manager approval letter if required by per diem policy and not already present
            if (policy.requiredDocs.includes("Manager Approval Letter")) {
                const hasLetter = docs.some(d => d.type === "manager_approval_letter");
                if (!hasLetter) {
                    docs.push({
                        type: "manager_approval_letter",
                        name: "Manager Approval Letter",
                        required: true,
                        url: claim.manager_approval_letter_url
                    });
                } else {
                    docs.forEach(d => {
                        if (d.type === "manager_approval_letter") {
                            d.required = true;
                        }
                    });
                }
            }

            return docs;
        }

        async function uploadDocument(sessionId, docType, inputElement) {
            if (!inputElement.files || inputElement.files.length === 0) return;
            const file = inputElement.files[0];
            
            const btnLabel = document.getElementById(`upload-btn-${sessionId}-${docType}`);
            const originalHTML = btnLabel.innerHTML;
            btnLabel.style.pointerEvents = "none";
            btnLabel.innerHTML = `<div class="spinner" style="width:12px; height:12px; border-width:1.5px; margin:0; display:inline-block; vertical-align:middle;"></div>`;
            
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const response = await fetch(`/api/upload/${sessionId}/${docType}`, {
                    method: "POST",
                    body: formData
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || "Upload failed");
                }
                
                showToast(`${file.name} uploaded successfully!`, "success");
                await fetchPendingApprovals();
            } catch (err) {
                console.error("Document upload failed", err);
                showToast("Upload failed: " + err.message, "error");
                btnLabel.innerHTML = originalHTML;
                btnLabel.style.pointerEvents = "all";
            }
        }

        let pendingSourceFilter = "all";

        function setPendingSourceFilter(src) {
            pendingSourceFilter = src;
            const buttons = ["all", "employee_portal", "report_workflow", "legacy_cli"];
            buttons.forEach(bId => {
                const btn = document.getElementById(`src-btn-${bId}`);
                if (btn) {
                    if (bId === src) {
                        btn.classList.add("active");
                    } else {
                        btn.classList.remove("active");
                    }
                }
            });
            fetchPendingApprovals();
        }
        window.setPendingSourceFilter = setPendingSourceFilter;

        async function fetchPendingApprovals(force = false) {
            const grid = document.getElementById("dashboard-grid");
            const countBadge = document.getElementById("pending-count");
            const hiddenBadge = document.getElementById("hidden-badge");
            const hiddenCountEl = document.getElementById("hidden-count");
            
            try {
                let url = `/api/pending?source=${pendingSourceFilter}`;
                if (force) {
                    url += "&refresh=true";
                }
                const response = await fetch(url);
                if (!response.ok) throw new Error("HTTP error " + response.status);
                
                const data = await response.json();
                
                if (data.warning) {
                    showToast(data.warning, "error");
                }
                
                if (force) {
                    // Trigger a forced refresh on the expense history list too
                    fetchExpenseHistory(true);
                }
                
                const claims = data.pending_claims;
                const hiddenCount = data.hidden_cli_sessions_count;
                
                countBadge.textContent = claims.length;
                
                if (hiddenCount > 0) {
                    hiddenCountEl.textContent = hiddenCount;
                    hiddenBadge.style.display = "flex";
                } else {
                    hiddenBadge.style.display = "none";
                }
                
                grid.innerHTML = "";
                cachedClaims = {};
                
                if (claims.length === 0) {
                    grid.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-icon">🎉</div>
                            <h3>All Caught Up!</h3>
                            <p>No claims are currently pending manager validation. All high-value transactions have been resolved.</p>
                        </div>
                    `;
                    return;
                }
                
                claims.forEach((claim, idx) => {
                    try {
                        cachedClaims[claim.session_id] = claim;
                        
                        const initials = claim.employee_name
                            .split("@")[0]
                            .split(".")
                            .map(n => n[0])
                            .join("")
                            .toUpperCase()
                            .substring(0, 3) || "EX";
                            
                        const avatarGradientClass = `gradient-avatar-${Math.abs(claim.employee_name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)) % 6}`;
                        
                        const policy = runPolicyCheck(claim);
                        const docsConfig = getDocumentsConfig(claim, policy);
                        
                        const card = document.createElement("div");
                        card.className = "approval-card";
                        card.id = `card-${claim.session_id}`;
                        card.style.animationDelay = `${idx * 0.1}s`;
                        
                        card.innerHTML = `
                            <div class="card-loader" id="loader-${claim.session_id}">
                                <div class="spinner"></div>
                                <div class="loader-text">Resuming Agent Runtime...</div>
                            </div>
                            <div class="card-header">
                                <div class="claimant-avatar ${avatarGradientClass}">${initials}</div>
                                <div class="claimant-info">
                                    <h3>${escapeHtml(claim.employee_name)}</h3>
                                    <p>Session: ${claim.session_id.substring(0, 8)}...</p>
                                </div>
                                <div class="amount-tag">${formatMoney(claim.amount)}</div>
                            </div>
                            <div class="card-body">
                                <p class="claim-desc">"${escapeHtml(claim.description)}"</p>
                                <div class="claim-participants-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin: 1rem 0; padding: 0.8rem; border-radius: 12px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); font-size: 0.8rem;">
                                    <div>
                                        <span style="display: block; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.15rem;">Employee</span>
                                        <span style="font-weight: 600; color: #e0e7ff;">${escapeHtml(claim.employee_name || 'N/A')}</span>
                                        <span style="display: block; font-size: 0.72rem; color: var(--text-muted); overflow-wrap: break-word; word-break: break-all;">${escapeHtml(claim.employee_email || 'N/A')}</span>
                                    </div>
                                    <div>
                                        <span style="display: block; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.15rem;">Assigned Manager</span>
                                        <span style="font-weight: 600; color: #e0e7ff; overflow-wrap: break-word; word-break: break-all;">${escapeHtml(claim.manager_email || 'None')}</span>
                                    </div>
                                    <div>
                                        <span style="display: block; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.15rem;">Submitted By</span>
                                        <span style="font-weight: 600; color: #cbd5e1; overflow-wrap: break-word; word-break: break-all;">${escapeHtml(claim.submitted_by_email || 'System')}</span>
                                        <span style="display: block; font-size: 0.72rem; color: #a5b4fc; font-weight: 500;">Role: ${escapeHtml(claim.submitted_by_role || 'user')}</span>
                                    </div>
                                    <div>
                                        <span style="display: block; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.15rem;">Reviewer Info</span>
                                        ${claim.reviewer_email ? `
                                            <span style="font-weight: 600; color: #cbd5e1; overflow-wrap: break-word; word-break: break-all;">${escapeHtml(claim.reviewer_email)}</span>
                                            <span style="display: block; font-size: 0.72rem; color: #f472b6; font-weight: 500;">Role: ${escapeHtml(claim.reviewer_role || 'reviewer')}</span>
                                        ` : `
                                            <span style="color: var(--text-muted); font-style: italic;">Not yet reviewed</span>
                                        `}
                                    </div>
                                </div>
                                <div class="meta-list" style="margin-bottom: 1rem;">
                                    <div class="meta-item">
                                        <strong>Interrupt ID:</strong> ${escapeHtml(claim.interrupt_id)}
                                    </div>
                                    <div class="meta-item">
                                        <strong>Prompt Role:</strong> ${escapeHtml(claim.user_id)}
                                    </div>
                                </div>
                                
                                <!-- Policy Review details -->
                                <div class="policy-review-box" style="margin-top: 1rem; padding: 1rem; border-radius: 12px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05);">
                                    <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem;">
                                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                        </svg>
                                        Policy Review
                                    </h4>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem; margin-bottom: 0.6rem;">
                                        <div><strong>Category:</strong> ${escapeHtml(policy.category)}</div>
                                        <div><strong>Status:</strong> <span style="color: ${policy.isValid ? '#34d399' : '#fb7185'}; font-weight: 600;">${policy.status}</span></div>
                                        ${policy.nights ? `<div><strong>Hotel Nights:</strong> ${policy.nights}</div>` : ''}
                                        ${policy.costPerNight ? `<div><strong>Nightly Cost:</strong> ${formatMoney(policy.costPerNight)}</div>` : ''}
                                    </div>
                                    
                                    ${policy.requiredDocs.length > 0 ? `
                                    <div style="font-size: 0.8rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.5rem; margin-top: 0.5rem;">
                                        <strong>Documents:</strong>
                                        <ul style="list-style: none; margin-top: 0.2rem; display: flex; flex-direction: column; gap: 0.25rem;">
                                            ${policy.requiredDocs.map(doc => {
                                                const isMissing = policy.missingDocs.includes(doc);
                                                return `<li style="display: flex; align-items: center; gap: 0.3rem; color: ${isMissing ? '#f43f5e' : '#10b981'};">
                                                    <span>${isMissing ? '✕' : '✓'}</span> ${doc}
                                                </li>`;
                                            }).join('')}
                                        </ul>
                                    </div>
                                    ` : ''}
                                    
                                    ${policy.warnings.map(w => `
                                    <div style="margin-top: 0.6rem; padding: 0.5rem 0.8rem; border-radius: 8px; background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.2); color: #fb7185; font-size: 0.75rem; line-height: 1.4; display: flex; align-items: flex-start; gap: 0.4rem;">
                                        <span style="font-size: 0.9rem; line-height: 1;">⚠️</span>
                                        <span>${escapeHtml(w)}</span>
                                    </div>
                                    `).join('')}
                                </div>

                                <!-- Office Supplies Review -->
                                ${policy.isOffice ? `
                                <div class="office-review-box" style="margin-top: 0.8rem; padding: 1rem; border-radius: 12px; background: rgba(99, 102, 241, 0.04); border: 1px solid rgba(99, 102, 241, 0.15);">
                                    <h4 style="font-size: 0.85rem; text-transform: uppercase; color: #a5b4fc; letter-spacing: 0.05em; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem; font-weight: 700;">
                                        💼 Office Expense Review
                                    </h4>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem;">
                                        <div><strong>Item Type:</strong> ${escapeHtml(claim.item_type || 'N/A')}</div>
                                        <div><strong>Vendor:</strong> ${escapeHtml(claim.vendor || 'N/A')}</div>
                                        <div><strong>Quantity:</strong> ${claim.quantity != null ? claim.quantity : 'N/A'}</div>
                                        <div><strong>Amount:</strong> ${formatMoney(claim.amount)}</div>
                                        <div style="grid-column: span 2;"><strong>Business Purpose:</strong> ${escapeHtml(claim.business_purpose || 'N/A')}</div>
                                    </div>
                                </div>
                                ` : ''}

                                <!-- Parking Expense Review -->
                                ${(policy.isParking || policy.isCitation) ? `
                                <div class="parking-review-box" style="margin-top: 0.8rem; padding: 1rem; border-radius: 12px; background: rgba(139, 92, 246, 0.04); border: 1px solid rgba(139, 92, 246, 0.15);">
                                    <h4 style="font-size: 0.85rem; text-transform: uppercase; color: #c084fc; letter-spacing: 0.05em; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem; font-weight: 700;">
                                        🚗 Parking Expense Review
                                    </h4>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem;">
                                        <div><strong>Location:</strong> ${escapeHtml(claim.parking_location || 'N/A')}</div>
                                        <div><strong>Date:</strong> ${escapeHtml(claim.parking_date || 'N/A')}</div>
                                        <div style="grid-column: span 2;"><strong>Business Purpose:</strong> ${escapeHtml(claim.business_purpose || 'N/A')}</div>
                                        ${claim.non_reimbursable_reason ? `<div style="grid-column: span 2; color: #fb7185;"><strong>Non-Reimbursable Reason:</strong> ${escapeHtml(claim.non_reimbursable_reason)}</div>` : ''}
                                    </div>
                                </div>
                                ` : ''}
                                
                                <!-- Per Diem Review Section -->
                                ${claim.per_diem_review ? `
                                <div class="per-diem-review-box" style="margin-top: 1rem; padding: 1.2rem; border-radius: 14px; background: rgba(99, 102, 241, 0.03); border: 1px solid rgba(99, 102, 241, 0.1); box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.2);">
                                    <h4 style="font-size: 0.85rem; text-transform: uppercase; color: #a5b4fc; letter-spacing: 0.05em; margin-bottom: 0.8rem; display: flex; align-items: center; gap: 0.4rem; font-weight: 700;">
                                        📅 Per Diem Review
                                    </h4>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem 1rem; font-size: 0.8rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 0.8rem; margin-bottom: 0.8rem;">
                                        <div><strong style="color: var(--text-muted);">Company Name:</strong> <span style="color: #e0e7ff; font-weight: 500;">${escapeHtml(claim.per_diem_review.company_name || 'N/A')}</span></div>
                                        <div><strong style="color: var(--text-muted);">Employee:</strong> <span style="color: #e0e7ff; font-weight: 500;">${escapeHtml(claim.per_diem_review.employee_name || claim.employee_name)}</span></div>
                                        <div><strong style="color: var(--text-muted);">Email:</strong> <span style="color: #c7d2fe; font-size: 0.75rem;">${escapeHtml(claim.per_diem_review.employee_email || '')}</span></div>
                                        <div><strong style="color: var(--text-muted);">Destination:</strong> <span style="color: #e0e7ff; font-weight: 500;">${escapeHtml(claim.per_diem_review.city || 'N/A')}, ${escapeHtml(claim.per_diem_review.state || 'N/A')}</span></div>
                                        <div><strong style="color: var(--text-muted);">Travel Dates:</strong> <span style="color: #c7d2fe; font-size: 0.75rem;">${claim.per_diem_review.travel_start_date ? claim.per_diem_review.travel_start_date.substring(0,10) : 'N/A'} to ${claim.per_diem_review.travel_end_date ? claim.per_diem_review.travel_end_date.substring(0,10) : 'N/A'}</span></div>
                                        <div><strong style="color: var(--text-muted);">Travel Duration:</strong> <span style="color: #e0e7ff; font-weight: 500;">${claim.per_diem_review.travel_days} days (${claim.per_diem_review.hotel_nights} nights)</span></div>
                                        <div style="grid-column: span 2;"><strong style="color: var(--text-muted);">Policy Source:</strong> <span class="badge" style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 0.15rem 0.5rem; border-radius: 6px; font-weight: 600; font-size: 0.7rem; border: 1px solid rgba(99,102,241,0.3); text-transform: uppercase;">${escapeHtml(claim.per_diem_review.policy_source || 'N/A')}</span></div>
                                    </div>

                                    <div style="margin-bottom: 0.8rem;">
                                        <table style="width: 100%; border-collapse: collapse; font-size: 0.75rem; color: #cbd5e1; text-align: left;">
                                            <thead>
                                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); color: var(--text-muted); font-weight: 600;">
                                                    <th style="padding: 0.4rem 0;">Category</th>
                                                    <th style="padding: 0.4rem 0; text-align: right;">Rate / Limit</th>
                                                    <th style="padding: 0.4rem 0; text-align: right;">Allowed</th>
                                                    <th style="padding: 0.4rem 0; text-align: right;">Claimed</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                                                    <td style="padding: 0.4rem 0;">Meals</td>
                                                    <td style="padding: 0.4rem 0; text-align: right;">${formatMoney(claim.per_diem_review.meal_rate_per_day)}/day</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; color: #a5b4fc;">${formatMoney(claim.per_diem_review.allowed_meal_total)}</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; font-weight: 500;">${formatMoney(claim.per_diem_review.claimed_meals)}</td>
                                                </tr>
                                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                                                    <td style="padding: 0.4rem 0;">Lodging</td>
                                                    <td style="padding: 0.4rem 0; text-align: right;">${formatMoney(claim.per_diem_review.lodging_rate_per_night)}/night</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; color: #a5b4fc;">${formatMoney(claim.per_diem_review.allowed_lodging_total)}</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; font-weight: 500;">${formatMoney(claim.per_diem_review.claimed_lodging)}</td>
                                                </tr>
                                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                                                    <td style="padding: 0.4rem 0;">Incidentals</td>
                                                    <td style="padding: 0.4rem 0; text-align: right;">${formatMoney(claim.per_diem_review.incidental_rate_per_day)}/day</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; color: #a5b4fc;">${formatMoney(claim.per_diem_review.allowed_incidental_total)}</td>
                                                    <td style="padding: 0.4rem 0; text-align: right; font-weight: 500;">${formatMoney(claim.per_diem_review.claimed_incidentals)}</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>

                                    <div style="display: flex; flex-direction: column; gap: 0.4rem; padding-top: 0.6rem; border-top: 1px solid rgba(255,255,255,0.05); font-size: 0.8rem;">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <span style="color: var(--text-muted); font-size: 0.75rem;">Total Claimed Amount:</span>
                                            <span style="color: white; font-weight: 600;">${formatMoney(claim.per_diem_review.claimed_amount)}</span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <span style="color: var(--text-muted); font-size: 0.75rem;">Allowed Per Diem Total:</span>
                                            <span style="color: #818cf8; font-weight: 600;">${formatMoney(safeNumber(claim.per_diem_review.allowed_meal_total) + safeNumber(claim.per_diem_review.allowed_lodging_total) + safeNumber(claim.per_diem_review.allowed_incidental_total))}</span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <span style="color: var(--text-muted); font-size: 0.75rem;">Overage / Overage Status:</span>
                                            <span style="color: ${claim.per_diem_review.overage_total > 0 ? '#fb7185' : '#34d399'}; font-weight: 600;">
                                                ${claim.per_diem_review.overage_total > 0 ? `+${formatMoney(claim.per_diem_review.overage_total)} (Exceeds)` : 'Within budget'}
                                            </span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.2rem;">
                                            <span style="color: var(--text-muted); font-size: 0.75rem;">Per Diem Review Status:</span>
                                            <span class="badge" style="background: ${
                                                claim.per_diem_review.status === 'Within company per diem' ? 'rgba(16,185,129,0.15)' :
                                                claim.per_diem_review.status === 'Exceeds company per diem' ? 'rgba(244,63,94,0.15)' :
                                                claim.per_diem_review.status === 'Requires manager approval' ? 'rgba(99,102,241,0.15)' :
                                                'rgba(245,158,11,0.15)'
                                            }; color: ${
                                                claim.per_diem_review.status === 'Within company per diem' ? '#34d399' :
                                                claim.per_diem_review.status === 'Exceeds company per diem' ? '#fb7185' :
                                                claim.per_diem_review.status === 'Requires manager approval' ? '#a5b4fc' :
                                                '#fbbf24'
                                            }; padding: 0.15rem 0.5rem; border-radius: 6px; font-weight: 600; font-size: 0.7rem; border: 1px solid currentColor;">
                                                ${escapeHtml(claim.per_diem_review.status)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                ` : ''}

                                <!-- Document Verification Box with Upload -->
                                <div class="document-verification-box" style="margin-top: 1rem; padding: 1rem; border-radius: 12px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05);">
                                    <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; margin-bottom: 0.8rem; display: flex; align-items: center; gap: 0.4rem; font-weight: 700;">
                                        📂 Required Documents
                                    </h4>
                                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                        ${docsConfig.map(doc => {
                                            return `
                                            <div class="doc-row" style="display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 0.8rem; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04); border-radius: 10px; gap: 0.5rem;">
                                                <div style="display: flex; flex-direction: column;">
                                                    <span style="font-size: 0.85rem; font-weight: 600; color: white;">${doc.name}</span>
                                                    <span style="font-size: 0.75rem; color: ${doc.url ? '#10b981' : (doc.required ? '#fb7185' : 'var(--text-muted)')}; font-weight: 500;">
                                                        ${doc.url ? '✓ Uploaded' : (doc.required ? '✕ Required' : '○ Optional')}
                                                    </span>
                                                </div>
                                                <div style="display: flex; gap: 0.4rem; align-items: center;">
                                                    ${doc.url ? `
                                                    <a href="${escapeHtml(doc.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; width: auto; flex: none; text-decoration: none;">
                                                        View
                                                    </a>
                                                    ` : ''}
                                                    <label class="btn-doc-upload" id="upload-btn-${claim.session_id}-${doc.type}" style="padding: 0.35rem 0.7rem; font-size: 0.75rem; border-radius: 8px; background: rgba(255,255,255,0.05); border: 1px solid var(--glass-border); color: var(--text-main); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.2rem; transition: var(--transition); user-select: none;">
                                                        <input type="file" onchange="uploadDocument('${claim.session_id}', '${doc.type}', this)" accept=".pdf,.png,.jpg,.jpeg" style="display: none;">
                                                        <span>${doc.url ? 'Replace' : 'Upload'}</span>
                                                    </label>
                                                </div>
                                            </div>
                                            `;
                                        }).join('')}
                                    </div>
                                </div>
                            </div>

                            <!-- Override Reason Box (finance_admin only) -->
                            ${(() => {
                                const isOverLimit = claim.per_diem_review && claim.per_diem_review.status === "Exceeds company per diem" && !claim.per_diem_review.manager_letter_uploaded;
                                const showOverrideInput = isOverLimit && USER_ROLE === "finance_admin";
                                if (showOverrideInput) {
                                    return `
                                    <div class="override-box" style="margin: 0.8rem 1.8rem 0 1.8rem; padding: 0.8rem; border-radius: 10px; background: rgba(245, 158, 11, 0.05); border: 1px solid rgba(245, 158, 11, 0.2);">
                                        <label style="font-size: 0.75rem; color: #f59e0b; font-weight: 600; text-transform: uppercase; display: block; margin-bottom: 0.4rem;">
                                            ⚠️ Finance Admin Policy Override
                                        </label>
                                        <input type="text" id="override-reason-${claim.session_id}" placeholder="Provide override reason (minimum 3 characters)..." 
                                            oninput="const btn = document.getElementById('approve-btn-${claim.session_id}'); const isValid = this.value.trim().length >= 3; btn.disabled = !isValid; btn.style.opacity = isValid ? '1' : '0.4'; btn.style.pointerEvents = isValid ? 'auto' : 'none';" 
                                            style="width: 100%; padding: 0.5rem 0.8rem; border-radius: 8px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: white; font-size: 0.8rem; outline: none; transition: var(--transition);"
                                            onfocus="this.style.borderColor='var(--primary)';" onblur="this.style.borderColor='rgba(255,255,255,0.1)';">
                                    </div>
                                    `;
                                }
                                return '';
                            })()}

                            <div class="card-actions" style="padding: 0 1.8rem 1.8rem 1.8rem; margin-top: 1rem;">
                                <button class="btn btn-reject" onclick="handleAction('${claim.session_id}', false)">
                                    Reject
                                </button>
                                <button class="btn btn-approve" id="approve-btn-${claim.session_id}" ${(() => {
                                    const isOverLimit = claim.per_diem_review && claim.per_diem_review.status === "Exceeds company per diem" && !claim.per_diem_review.manager_letter_uploaded;
                                    const showOverrideInput = isOverLimit && USER_ROLE === "finance_admin";
                                    if (showOverrideInput) {
                                        return 'disabled style="opacity: 0.4; cursor: not-allowed; pointer-events: none;"';
                                    } else if (!policy.isValid) {
                                        return 'disabled style="opacity: 0.4; cursor: not-allowed; pointer-events: none;"';
                                    }
                                    return '';
                                })()} onclick="handleAction('${claim.session_id}', true)">
                                    Approve Claim
                                </button>
                            </div>
                        `;
                        grid.appendChild(card);
                    } catch (cardErr) {
                        console.warn("Failed to render pending claim card for session_id:", claim.session_id, cardErr);
                    }
                });
                
            } catch (err) {
                console.error("Failed to load approvals", err);
                grid.innerHTML = `
                    <div class="empty-state" style="border-color: var(--danger-glow);">
                        <div class="empty-icon" style="filter:none;">❌</div>
                        <h3 style="color:#f43f5e;">System Sync Offline</h3>
                        <p>Error connecting to backend services: ${err.message}. Ensure your credentials are active and GCP_PROJECT is set.</p>
                    </div>
                `;
            }
        }

        async function handleAction(sessionId, approved) {
            const loader = document.getElementById(`loader-${sessionId}`);
            loader.style.display = "flex";
            
            const claim = cachedClaims[sessionId];
            const interruptId = claim ? claim.interrupt_id : "review_decision";
            
            let overrideReason = null;
            const overrideInput = document.getElementById(`override-reason-${sessionId}`);
            if (overrideInput) {
                overrideReason = overrideInput.value.trim();
            }
            
            try {
                const response = await fetch(`/api/action/${sessionId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ 
                        approved, 
                        interrupt_id: interruptId,
                        override_reason: overrideReason
                    })
                });
                
                if (!response.ok) throw new Error("HTTP Action error: " + response.status);
                
                const data = await response.json();
                
                showComplianceReview(claim, approved, data.final_review);
                showToast(approved ? "Claim approved successfully!" : "Claim rejected successfully.", "success");
                await fetchPendingApprovals();
                
            } catch (err) {
                console.error("Action execution failed", err);
                showToast("Action failed: " + err.message, "error");
                loader.style.display = "none";
            }
        }

        function showComplianceReview(claim, approved, finalReview) {
            const claimantEl = document.getElementById("modal-claimant");
            const amountEl = document.getElementById("modal-amount");
            const sessionEl = document.getElementById("modal-session-id");
            const statusBox = document.getElementById("modal-status-box");
            const statusIcon = document.getElementById("modal-status-icon");
            const statusTitle = document.getElementById("modal-status-title");
            const statusDesc = document.getElementById("modal-status-desc");
            const commentsEl = document.getElementById("modal-comments");
            const receiptContainer = document.getElementById("modal-receipt-container");
            
            sessionEl.textContent = `Session Reference: ${claim.session_id}`;
            claimantEl.textContent = claim.employee_name;
            amountEl.textContent = formatMoney(claim.amount);
            commentsEl.textContent = finalReview;
            
            const docList = [];
            if (claim.receipt_url) docList.push(`<a href="${claim.receipt_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; display: flex; align-items: center; justify-content: center;">📄 View Receipt</a>`);
            if (claim.office_receipt_url) docList.push(`<a href="${claim.office_receipt_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; display: flex; align-items: center; justify-content: center;">💼 View Office Receipt</a>`);
            if (claim.parking_receipt_url) docList.push(`<a href="${claim.parking_receipt_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; display: flex; align-items: center; justify-content: center;">🚗 View Parking Receipt</a>`);
            if (claim.hotel_receipt_url) docList.push(`<a href="${claim.hotel_receipt_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; display: flex; align-items: center; justify-content: center;">🏨 View Hotel Receipt</a>`);
            if (claim.flight_ticket_receipt_url) docList.push(`<a href="${claim.flight_ticket_receipt_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; display: flex; align-items: center; justify-content: center;">✈️ View Flight Receipt</a>`);
            if (claim.manager_approval_letter_url) docList.push(`<a href="${claim.manager_approval_letter_url}" target="_blank" rel="noopener noreferrer" class="btn btn-receipt" style="flex: 1; padding: 0.5rem; text-decoration: none; border-color: rgba(99, 102, 241, 0.4); background: rgba(99, 102, 241, 0.15); display: flex; align-items: center; justify-content: center;">✉️ View Approval Letter</a>`);
            
            if (docList.length > 0) {
                receiptContainer.innerHTML = `<div style="display: flex; flex-wrap: wrap; gap: 0.5rem; width: 100%;">${docList.join('')}</div>`;
                receiptContainer.style.display = "block";
            } else {
                receiptContainer.style.display = "none";
            }
            
            if (approved) {
                statusBox.className = "status-box approved";
                statusIcon.textContent = "✓";
                statusTitle.textContent = "Claim Approved";
                statusDesc.textContent = "Authorized on Agent Runtime. Automated payout scheduled.";
            } else {
                statusBox.className = "status-box rejected";
                statusIcon.textContent = "✕";
                statusTitle.textContent = "Claim Rejected";
                statusDesc.textContent = "Declined on Agent Runtime. Notification sent to claimant.";
            }
            
            toggleModal(true);
        }

        function toggleModal(active) {
            const overlay = document.getElementById("slide-overlay");
            const modal = document.getElementById("slide-modal");
            
            if (active) {
                overlay.classList.add("active");
                modal.classList.add("active");
            } else {
                overlay.classList.remove("active");
                modal.classList.remove("active");
            }
        }

        function showToast(message, type) {
            const toast = document.getElementById("toast");
            const toastText = document.getElementById("toast-text");
            
            toastText.textContent = message;
            toast.className = `toast toast-${type} active`;
            
            setTimeout(() => {
                toast.classList.remove("active");
            }, 4000);
        }

        function escapeHtml(str) {
            if (!str) return "";
            return str
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

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
fetchPendingApprovals = async function(force = false) {
    // Run original to fetch individual claims
    await originalFetchPendingApprovals(force);
    
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
        const widgetsPanel = document.getElementById("manager-widgets-panel");
        const managerDateFilters = document.getElementById("manager-date-filters");

        if (USER_ROLE === "manager" || USER_ROLE === "finance_admin") {
            if (filterBar) filterBar.style.display = "flex";
            if (widgetsPanel) widgetsPanel.style.display = "grid";
            if (managerDateFilters) managerDateFilters.style.display = "flex";
        } else {
            if (filterBar) filterBar.style.display = "none";
            if (widgetsPanel) widgetsPanel.style.display = "none";
            if (managerDateFilters) managerDateFilters.style.display = "none";
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
        // Date filter
        if (typeof isReportInDateFilter === 'function' && !isReportInDateFilter(r)) return false;

        if (employeeVal && !r.employee_name.toLowerCase().includes(employeeVal) && !r.employee_email.toLowerCase().includes(employeeVal)) return false;
        if (managerVal && !r.manager_email.toLowerCase().includes(managerVal)) return false;
        if (deptVal && r.department !== deptVal) return false;
        if (statusVal && r.status !== statusVal) return false;
        return true;
    });

    renderReportsGrid(filtered);

    // Update manager widgets based on reports matching the date filter
    if (USER_ROLE === "manager" || USER_ROLE === "finance_admin") {
        const dateFiltered = allReports.filter(r => {
            if (typeof isReportInDateFilter === 'function') {
                return isReportInDateFilter(r);
            }
            return true;
        });
        if (typeof updateManagerWidgets === 'function') {
            updateManagerWidgets(dateFiltered);
        }
    }
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
            case 'submitted':
                statusBadge = `<span class="badge" style="background: rgba(59, 130, 246, 0.1); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.25);">Submitted</span>`;
                break;
            case 'pending_manager_review':
                statusBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.25);">Reviewing</span>`;
                break;
            case 'returned_to_employee':
                statusBadge = `<span class="badge" style="background: rgba(244, 63, 94, 0.15); color: #fda4af; border: 1px solid rgba(244, 63, 94, 0.3);">Returned</span>`;
                break;
            case 'approved_by_manager':
            case 'approved':
                statusBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);">Approved (Mgr)</span>`;
                break;
            case 'approved_with_exceptions':
                statusBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.35);">Approved (Exceptions)</span>`;
                break;
            case 'rejected':
                statusBadge = `<span class="badge" style="background: rgba(244, 63, 94, 0.1); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.25);">Rejected</span>`;
                break;
            case 'paid':
                statusBadge = `<span class="badge" style="background: rgba(147, 51, 234, 0.15); color: #c084fc; border: 1px solid rgba(147, 51, 234, 0.3);">Paid</span>`;
                break;
            case 'closed':
                statusBadge = `<span class="badge" style="background: rgba(107, 114, 128, 0.15); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.3);">Closed</span>`;
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
    const missingDocs = parseInt(document.getElementById("stat-missing-documents").textContent || "0", 10);
    const exceptions = parseInt(document.getElementById("stat-policy-exceptions").textContent || "0", 10);
    
    let overrideReason = "";
    if (missingDocs > 0 || exceptions > 0) {
        overrideReason = prompt("This report contains policy exceptions or missing documents. An override reason is required from a manager or finance admin to proceed with approval:");
        if (overrideReason === null) return; // User clicked Cancel
        if (!overrideReason.trim()) {
            alert("Approval aborted: An override reason must be provided for non-compliant reports.");
            return;
        }
    } else {
        if (!confirm("Are you sure you want to approve this entire expense report? All non-rejected claims will be marked as approved.")) return;
    }
    
    try {
        const response = await fetch(`/api/reports/${activeReportId}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ override_reason: overrideReason })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Approval failed");
        }
        
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


/* ==========================================================================
   MANAGER EXPENSE REPORT SUMMARY WIDGETS & DATE FILTERS
   ========================================================================== */

let selectedManagerDateFilter = 'all';

function isReportInDateFilter(r) {
    if (selectedManagerDateFilter === 'all') return true;
    
    // Parse the date. r.updated_at is preferred, fallback to r.created_at, then r.report_period_start
    const dateStr = r.updated_at || r.created_at || r.report_period_start;
    if (!dateStr) return true;
    
    const rDate = new Date(dateStr);
    const now = new Date();
    
    // Normalize to compare dates cleanly
    if (selectedManagerDateFilter === 'weekly') {
        const limit = new Date();
        limit.setDate(limit.getDate() - 7);
        return rDate >= limit;
    }
    if (selectedManagerDateFilter === 'monthly') {
        const limit = new Date();
        limit.setDate(limit.getDate() - 30);
        return rDate >= limit;
    }
    if (selectedManagerDateFilter === 'quarterly') {
        const limit = new Date();
        limit.setDate(limit.getDate() - 90);
        return rDate >= limit;
    }
    if (selectedManagerDateFilter === 'custom') {
        const startVal = document.getElementById("manager-custom-start").value;
        const endVal = document.getElementById("manager-custom-end").value;
        if (!startVal || !endVal) return true; // Don't filter if incomplete
        
        const start = new Date(startVal + "T00:00:00");
        const end = new Date(endVal + "T23:59:59");
        return rDate >= start && rDate <= end;
    }
    return true;
}

function updateManagerWidgets(reports) {
    const panel = document.getElementById("manager-widgets-panel");
    if (!panel) return;
    
    // 1. Total reports submitted (all reports with non-draft status)
    const totalSubmitted = reports.filter(r => r.status !== 'draft').length;
    
    // 2. Approved reports (approved, paid, closed, etc.)
    const approved = reports.filter(r => ['approved', 'approved_by_manager', 'approved_with_exceptions', 'paid', 'closed'].includes(r.status)).length;
    
    // 3. Pending manager approval
    const pending = reports.filter(r => ['pending_manager_review', 'submitted'].includes(r.status));
    const pendingCount = pending.length;
    
    // Calculate overdue (pending for more than 7 days)
    const overdueCount = pending.filter(r => {
        const dateStr = r.submitted_at || r.updated_at || r.created_at;
        if (!dateStr) return false;
        const age = Date.now() - new Date(dateStr).getTime();
        return age > 7 * 24 * 60 * 60 * 1000;
    }).length;
    
    // 4. Rejected reports
    const rejected = reports.filter(r => r.status === 'rejected').length;
    
    // 5. New / most recent reports (submitted/review within last 3 days)
    const recent = reports.filter(r => {
        const dateStr = r.submitted_at || r.updated_at || r.created_at;
        if (!dateStr) return false;
        const age = Date.now() - new Date(dateStr).getTime();
        return age <= 3 * 24 * 60 * 60 * 1000 && ['submitted', 'pending_manager_review'].includes(r.status);
    }).length;
    
    // 6. Reports missing required information
    const missingInfo = reports.filter(r => (r.missing_document_count || 0) > 0).length;
    
    // 7. Reports with blocked or unresolved items
    const blockedOrUnresolved = reports.filter(r => (r.policy_exception_count || 0) > 0 || r.status === 'returned_to_employee' || r.status === 'blocked_missing_docs').length;
    
    // Construct the 7 widget cards
    panel.innerHTML = `
        <!-- Card 1: Total Submitted -->
        <div class="widget-card widget-total">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="widget-title">Total Submitted</span>
                <span class="widget-icon">📊</span>
            </div>
            <div class="widget-value">${totalSubmitted}</div>
            <div class="widget-trend">All non-draft reports</div>
        </div>
        
        <!-- Card 2: Approved (Healthy/Green) -->
        <div class="widget-card widget-approved">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="widget-title" style="color: var(--success);">Approved</span>
                <span class="widget-icon">✅</span>
            </div>
            <div class="widget-value" style="color: var(--success);">${approved}</div>
            <div class="widget-trend" style="color: rgba(16, 185, 129, 0.7);">Ready / Settled</div>
        </div>
        
        <!-- Card 3: Pending Manager Approval (Warning/Amber) -->
        <div class="widget-card widget-pending">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="widget-title" style="color: #f59e0b;">Pending Approval</span>
                <span class="widget-icon">⏳</span>
            </div>
            <div class="widget-value" style="color: #f59e0b;">${pendingCount}</div>
            <div class="widget-trend" style="color: ${overdueCount > 0 ? 'var(--danger)' : '#f59e0b'}; font-weight: ${overdueCount > 0 ? '700' : 'normal'};">
                ${overdueCount > 0 ? `⚠️ ${overdueCount} Overdue (>7d)` : 'Needs action'}
            </div>
        </div>
        
        <!-- Card 4: Rejected (Red/Danger) -->
        <div class="widget-card widget-rejected">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="widget-title" style="color: var(--danger);">Rejected</span>
                <span class="widget-icon">❌</span>
            </div>
            <div class="widget-value" style="color: var(--danger);">${rejected}</div>
            <div class="widget-trend" style="color: rgba(244, 63, 94, 0.7);">Declined reports</div>
        </div>
        
        <!-- Card 5: New / Most Recent (Indigo) -->
        <div class="widget-card widget-new">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="widget-title" style="color: #818cf8;">New & Recent</span>
                <span class="widget-icon">✨</span>
            </div>
            <div class="widget-value" style="color: #818cf8;">${recent}</div>
            <div class="widget-trend" style="color: rgba(129, 140, 248, 0.7);">Submitted <= 3 days ago</div>
        </div>
        
        <!-- Card 6: Missing Info (Warning/Orange) -->
        <div class="widget-card widget-missing">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="widget-title" style="color: #f97316;">Missing Info</span>
                <span class="widget-icon">📂</span>
            </div>
            <div class="widget-value" style="color: #f97316;">${missingInfo}</div>
            <div class="widget-trend" style="color: ${missingInfo > 0 ? '#f97316' : 'var(--text-muted)'}; font-weight: ${missingInfo > 0 ? '700' : 'normal'};">
                ${missingInfo > 0 ? '⚠️ Lacks required documents' : 'All documents present'}
            </div>
        </div>
        
        <!-- Card 7: Blocked / Unresolved (Red/Danger) -->
        <div class="widget-card widget-blocked">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="widget-title" style="color: #f43f5e;">Blocked & Unresolved</span>
                <span class="widget-icon">🚫</span>
            </div>
            <div class="widget-value" style="color: #f43f5e;">${blockedOrUnresolved}</div>
            <div class="widget-trend" style="color: ${blockedOrUnresolved > 0 ? '#f43f5e' : 'var(--text-muted)'}; font-weight: ${blockedOrUnresolved > 0 ? '700' : 'normal'};">
                ${blockedOrUnresolved > 0 ? '⚠️ Has unresolved exceptions' : 'Zero exceptions / blocks'}
            </div>
        </div>
    `;
}

function setManagerDateFilter(type) {
    selectedManagerDateFilter = type;
    
    // Toggle active class on date filter buttons
    document.querySelectorAll(".filter-tab-btn").forEach(btn => {
        btn.classList.remove("active");
    });
    
    const activeBtn = document.getElementById("filter-btn-" + type);
    if (activeBtn) {
        activeBtn.classList.add("active");
    }
    
    // Show/hide custom range inputs
    const customInputs = document.getElementById("manager-custom-date-inputs");
    if (type === 'custom') {
        if (customInputs) customInputs.style.display = "flex";
    } else {
        if (customInputs) customInputs.style.display = "none";
    }
    
    applyReportFilters();
}

function onManagerCustomDateChange() {
    applyReportFilters();
}


/* ==========================================================================
   BUSINESS CREDIT CARD INTEGRATION
   ========================================================================== */

let allCardTransactions = [];
let cardTxFilterStatus = 'all';

async function fetchCardTransactions() {
    const connectPanel = document.getElementById("connect-card-panel");
    if (connectPanel) {
        if (typeof USER_ROLE !== "undefined" && USER_ROLE === "finance_admin") {
            connectPanel.style.display = "block";
        } else {
            connectPanel.style.display = "none";
        }
    }
    try {
        const response = await fetch("/api/cards/transactions");
        if (!response.ok) {
            throw new Error("Failed to fetch credit card transactions");
        }
        allCardTransactions = await response.json();
        applyCardTxFilters();
    } catch (err) {
        console.error("Error fetching card transactions:", err);
        showToast("Error loading credit card transactions: " + err.message, "error");
    }
}

function applyCardTxFilters() {
    const searchVal = (document.getElementById("card-search-input")?.value || "").toLowerCase();
    
    const filtered = allCardTransactions.filter(tx => {
        // Status filter
        if (cardTxFilterStatus !== 'all' && tx.reconciliation_status !== cardTxFilterStatus) {
            return false;
        }
        // Search filter
        if (searchVal) {
            const merchant = (tx.merchant || "").toLowerCase();
            const holder = (tx.cardholder_name || "").toLowerCase();
            const email = (tx.cardholder_email || "").toLowerCase();
            const last4 = (tx.card_last4 || "").toLowerCase();
            const provider = (tx.provider || "").toLowerCase();
            if (!merchant.includes(searchVal) && 
                !holder.includes(searchVal) && 
                !email.includes(searchVal) && 
                !last4.includes(searchVal) && 
                !provider.includes(searchVal)) {
                return false;
            }
        }
        return true;
    });
    
    renderCardTransactionsTable(filtered);
}

function setCardTxFilter(status) {
    cardTxFilterStatus = status;
    document.querySelectorAll('[id^="card-filter-"]').forEach(btn => {
        btn.classList.remove("active");
    });
    const activeBtn = document.getElementById("card-filter-" + status);
    if (activeBtn) {
        activeBtn.classList.add("active");
    }
    applyCardTxFilters();
}

function renderCardTransactionsTable(txs) {
    const tbody = document.getElementById("card-transactions-table-body");
    if (!tbody) return;
    
    if (txs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 3rem; color: var(--text-muted);">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">💳</div>
                    <h3>No Transactions Found</h3>
                    <p>Connect a mock card feed or adjust your filters.</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = txs.map(tx => {
        // Provider Badge Style
        let provBg = 'rgba(255,255,255,0.05)';
        let provColor = '#cbd5e1';
        const p = (tx.provider || "").toLowerCase();
        if (p.includes("ramp")) {
            provBg = 'rgba(16, 185, 129, 0.1)';
            provColor = '#10b981';
        } else if (p.includes("brex")) {
            provBg = 'rgba(245, 158, 11, 0.1)';
            provColor = '#f59e0b';
        } else if (p.includes("amex") || p.includes("american")) {
            provBg = 'rgba(59, 130, 246, 0.1)';
            provColor = '#3b82f6';
        } else if (p.includes("visa")) {
            provBg = 'rgba(139, 92, 246, 0.1)';
            provColor = '#8b5cf6';
        } else if (p.includes("mastercard")) {
            provBg = 'rgba(249, 115, 22, 0.1)';
            provColor = '#f97316';
        } else if (p.includes("stripe")) {
            provBg = 'rgba(99, 102, 241, 0.1)';
            provColor = '#6366f1';
        } else if (p.includes("plaid")) {
            provBg = 'rgba(20, 184, 166, 0.1)';
            provColor = '#20b8a6';
        }
        
        const providerBadge = `<span style="background: ${provBg}; color: ${provColor}; border: 1px solid ${provColor}33; padding: 0.25rem 0.5rem; border-radius: 6px; font-size: 0.75rem; font-weight: 700; display: inline-block;">${tx.provider}</span>`;
        
        // Reconciliation Badge
        let recBg = 'rgba(255,255,255,0.05)';
        let recColor = '#cbd5e1';
        let recText = 'Unreconciled';
        if (tx.reconciliation_status === 'matched') {
            recBg = 'rgba(59, 130, 246, 0.15)';
            recColor = '#93c5fd';
            recText = 'Matched';
        } else if (tx.reconciliation_status === 'reconciled') {
            recBg = 'rgba(16, 185, 129, 0.15)';
            recColor = '#34d399';
            recText = 'Reconciled';
        }
        const recBadge = `<span style="background: ${recBg}; color: ${recColor}; border: 1px solid ${recColor}33; padding: 0.25rem 0.5rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; display: inline-block;">${recText}</span>`;
        
        // Receipt Status UI
        let receiptHtml = '';
        if (tx.matched_receipt_url) {
            receiptHtml = `<div style="display: flex; align-items: center; gap: 0.3rem;">
                <span style="color: #10b981;">✓</span>
                <a href="${tx.matched_receipt_url}" target="_blank" rel="noopener noreferrer" style="color: #60a5fa; text-decoration: underline; font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 150px;" title="${tx.matched_receipt_name || 'Receipt'}">${tx.matched_receipt_name || 'Receipt'}</a>
            </div>`;
        } else {
            receiptHtml = `<button class="btn" style="padding: 0.2rem 0.4rem; font-size: 0.75rem; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.25); color: #f59e0b; border-radius: 6px; width: auto; height: auto; cursor: pointer;" onclick="openCardReceiptModal('${tx.transaction_id}')">+ Match Receipt</button>`;
        }
        
        // Claim Status UI
        let claimHtml = '';
        if (tx.matched_claim_id) {
            claimHtml = `<div style="margin-top: 0.3rem;"><span style="background: rgba(99,102,241,0.15); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.3); padding: 0.15rem 0.35rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600;">Linked: #${tx.matched_claim_id.substring(0, 8)}...</span></div>`;
        } else {
            claimHtml = `<div style="margin-top: 0.3rem;"><button class="btn" style="padding: 0.2rem 0.4rem; font-size: 0.75rem; background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.25); color: #60a5fa; border-radius: 6px; width: auto; height: auto; cursor: pointer;" onclick="openCardClaimModal('${tx.transaction_id}')">+ Attach Expense</button></div>`;
        }
        
        // Action buttons
        let actionsHtml = '';
        if (tx.reconciliation_status === 'matched') {
            actionsHtml = `<button class="btn btn-primary" style="padding: 0.3rem 0.6rem; font-size: 0.75rem; border-radius: 6px; cursor: pointer; width: auto; height: auto; font-weight: 600;" onclick="reconcileCardTransaction('${tx.transaction_id}')">Confirm Reconcile</button>`;
        } else if (tx.reconciliation_status === 'reconciled') {
            actionsHtml = `<span style="color: #10b981; font-size: 0.8rem; font-weight: 600;">✓ Reconciled</span>`;
        } else {
            actionsHtml = `<span style="color: var(--text-muted); font-size: 0.8rem;">Awaiting Link</span>`;
        }
        
        return `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.04); transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='rgba(255,255,255,0.01)'" onmouseout="this.style.backgroundColor='transparent'">
                <td style="padding: 1rem 0.75rem; vertical-align: top;">
                    <div style="font-weight: 700; color: white; font-size: 0.8rem; margin-bottom: 0.25rem;">${tx.transaction_id}</div>
                    ${providerBadge}
                </td>
                <td style="padding: 1rem 0.75rem; vertical-align: top;">
                    <div style="font-weight: 600; color: white;">${tx.cardholder_name}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.2rem;">${tx.cardholder_email}</div>
                    <div style="font-size: 0.75rem; font-family: monospace; color: var(--text-muted);">•••• ${tx.card_last4}</div>
                </td>
                <td style="padding: 1rem 0.75rem; color: white; font-weight: 500; vertical-align: top;">${tx.transaction_date}</td>
                <td style="padding: 1rem 0.75rem; vertical-align: top;">
                    <div style="font-weight: 700; color: white;">${tx.merchant}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); font-style: italic; margin-top: 0.15rem;">USD Feed</div>
                </td>
                <td style="padding: 1rem 0.75rem; color: white; font-weight: 700; font-size: 0.95rem; vertical-align: top;">$${parseFloat(tx.amount || 0).toFixed(2)}</td>
                <td style="padding: 1rem 0.75rem; vertical-align: top;">
                    <div style="display: flex; flex-direction: column; gap: 0.2rem;">
                        ${receiptHtml}
                        ${claimHtml}
                        <div style="margin-top: 0.4rem;">${recBadge}</div>
                    </div>
                </td>
                <td style="padding: 1rem 0.75rem; vertical-align: top; max-width: 200px;">
                    <div style="display: flex; align-items: flex-start; gap: 0.4rem;">
                        <span style="font-size: 0.8rem; color: var(--text-muted); overflow-wrap: break-word; word-break: break-all;" id="card-tx-notes-text-${tx.transaction_id}">${tx.notes || 'No notes added'}</span>
                        <button style="background: none; border: none; cursor: pointer; color: var(--text-muted); font-size: 0.8rem; padding: 0;" title="Edit Notes" onclick="editCardNotes('${tx.transaction_id}', '${escapeHtml(tx.notes || '')}')">✏️</button>
                    </div>
                </td>
                <td style="padding: 1rem 0.75rem; text-align: right; vertical-align: top;">
                    <div style="display: flex; gap: 0.5rem; justify-content: flex-end; align-items: center; min-height: 32px;">
                        ${actionsHtml}
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

async function connectBusinessCard(event) {
    if (event) event.preventDefault();
    
    const provider = document.getElementById("connect-card-provider").value;
    const cardholder_name = document.getElementById("connect-card-holder-name").value;
    const cardholder_email = document.getElementById("connect-card-holder-email").value;
    const card_last4 = document.getElementById("connect-card-last4").value;
    
    const payload = {
        provider,
        cardholder_name,
        cardholder_email,
        card_last4
    };
    
    try {
        const response = await fetch("/api/cards/connect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Connection failed");
        }
        
        showToast(`Connected ${provider} card feed and imported transactions successfully!`, "success");
        document.getElementById("connect-card-form").reset();
        fetchCardTransactions();
    } catch (err) {
        console.error(err);
        showToast("Error connecting feed: " + err.message, "error");
    }
}

function openCardReceiptModal(txId) {
    document.getElementById("card-receipt-tx-id").value = txId;
    document.getElementById("card-receipt-url").value = "";
    document.getElementById("card-receipt-name").value = "";
    
    document.getElementById("card-receipt-modal-overlay").style.opacity = "1";
    document.getElementById("card-receipt-modal-overlay").style.pointerEvents = "all";
    document.getElementById("modal-card-receipt").style.opacity = "1";
    document.getElementById("modal-card-receipt").style.pointerEvents = "all";
    document.getElementById("modal-card-receipt").style.transform = "translate(-50%, -50%) scale(1)";
}

function closeCardReceiptModal() {
    document.getElementById("card-receipt-modal-overlay").style.opacity = "0";
    document.getElementById("card-receipt-modal-overlay").style.pointerEvents = "none";
    document.getElementById("modal-card-receipt").style.opacity = "0";
    document.getElementById("modal-card-receipt").style.pointerEvents = "none";
    document.getElementById("modal-card-receipt").style.transform = "translate(-50%, -50%) scale(0.9)";
}

async function submitCardReceipt() {
    const transaction_id = document.getElementById("card-receipt-tx-id").value;
    const receipt_url = document.getElementById("card-receipt-url").value;
    const receipt_name = document.getElementById("card-receipt-name").value || "receipt.png";
    
    if (!receipt_url) {
        showToast("Please provide a receipt URL or path", "error");
        return;
    }
    
    try {
        const response = await fetch("/api/cards/match-receipt", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id, receipt_url, receipt_name })
        });
        
        if (!response.ok) throw new Error("Match receipt endpoint returned error");
        
        showToast("Receipt matched to credit card transaction!", "success");
        closeCardReceiptModal();
        fetchCardTransactions();
    } catch (err) {
        console.error(err);
        showToast("Error matching receipt: " + err.message, "error");
    }
}

async function openCardClaimModal(txId) {
    document.getElementById("card-claim-tx-id").value = txId;
    const select = document.getElementById("card-claim-select");
    if (select) {
        select.innerHTML = '<option value="">Loading claims...</option>';
    }
    
    document.getElementById("card-claim-modal-overlay").style.opacity = "1";
    document.getElementById("card-claim-modal-overlay").style.pointerEvents = "all";
    document.getElementById("modal-card-claim").style.opacity = "1";
    document.getElementById("modal-card-claim").style.pointerEvents = "all";
    document.getElementById("modal-card-claim").style.transform = "translate(-50%, -50%) scale(1)";
    
    // Load unattached claims
    try {
        const response = await fetch("/api/expenses");
        if (!response.ok) throw new Error("Failed to load expenses");
        const claims = await response.json();
        
        // Filter out claims that already have a card_transaction_id or payment_method="Business Card"
        const unattached = claims.filter(c => !c.card_transaction_id && c.payment_method !== "Business Card");
        
        if (unattached.length === 0) {
            select.innerHTML = '<option value="">No unattached claims found</option>';
        } else {
            select.innerHTML = unattached.map(c => `
                <option value="${c.claim_id}">${c.employee_name || 'Employee'} - ${c.merchant || 'Unknown'} - $${parseFloat(c.amount || 0).toFixed(2)} (${c.expense_date})</option>
            `).join("");
        }
    } catch (err) {
        console.error(err);
        select.innerHTML = '<option value="">Error loading claims</option>';
    }
}

function closeCardClaimModal() {
    document.getElementById("card-claim-modal-overlay").style.opacity = "0";
    document.getElementById("card-claim-modal-overlay").style.pointerEvents = "none";
    document.getElementById("modal-card-claim").style.opacity = "0";
    document.getElementById("modal-card-claim").style.pointerEvents = "none";
    document.getElementById("modal-card-claim").style.transform = "translate(-50%, -50%) scale(0.9)";
}

async function submitCardClaim() {
    const transaction_id = document.getElementById("card-claim-tx-id").value;
    const claim_id = document.getElementById("card-claim-select").value;
    
    if (!claim_id) {
        showToast("Please select a valid expense claim line item", "error");
        return;
    }
    
    try {
        const response = await fetch("/api/cards/attach-claim", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id, claim_id })
        });
        
        if (!response.ok) throw new Error("Attach claim endpoint returned error");
        
        showToast("Transaction successfully attached to expense claim line item!", "success");
        closeCardClaimModal();
        fetchCardTransactions();
    } catch (err) {
        console.error(err);
        showToast("Error linking claim: " + err.message, "error");
    }
}

async function reconcileCardTransaction(transaction_id) {
    try {
        const response = await fetch("/api/cards/reconcile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id })
        });
        
        if (!response.ok) throw new Error("Reconciliation request failed");
        
        showToast("Transaction status successfully finalized as RECONCILED!", "success");
        fetchCardTransactions();
    } catch (err) {
        console.error(err);
        showToast("Reconciliation failed: " + err.message, "error");
    }
}

async function editCardNotes(transaction_id, currentNotes) {
    const notes = prompt("Edit notes / description for this transaction:", currentNotes);
    if (notes === null) return; // User cancelled
    
    try {
        const response = await fetch("/api/cards/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id, notes })
        });
        
        if (!response.ok) throw new Error("Update request failed");
        
        showToast("Notes updated successfully!", "success");
        fetchCardTransactions();
    } catch (err) {
        console.error(err);
        showToast("Update failed: " + err.message, "error");
    }
}
