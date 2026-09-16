// Backend URL

const API_URL = "https://healthphc-6.onrender.com";

// HTML elements

const phcSelect = document.getElementById("phcSelect");

const inventoryContainer =
    document.getElementById("inventoryContainer");


// --------------------------------------------------
// LOAD PHCs
// --------------------------------------------------

async function loadPHCs() {

    try {

        const response =
            await fetch(`${API_URL}/phcs`);

        const phcs =
            await response.json();


        phcs.forEach(phc => {

            const option =
                document.createElement("option");

            option.value = phc.id;

            option.textContent =
                `${phc.name} - ${phc.district}`;

            phcSelect.appendChild(option);

        });

    }

    catch (error) {

        console.error("Error loading PHCs:", error);

    }

}
async function loadMedicines() {

    try {

        const response = await fetch(
            `${API_URL}/medicines/search?name=medicine`
        );

        const medicines = await response.json();

        const medicineSelect =
            document.getElementById("forecastMedicine");

        medicines.forEach(medicine => {

            const option =
                document.createElement("option");

            option.value = medicine.rxcui;

            option.textContent = medicine.name;

            medicineSelect.appendChild(option);
        });

    } catch (error) {

        console.error(
            "Error loading medicines:",
            error
        );
    }
}

// --------------------------------------------------
// LOAD INVENTORY
// --------------------------------------------------

async function loadInventory(phcId) {

    

    if (!phcId) {

        inventoryContainer.innerHTML = `
            <p class="message">
                Select a PHC to view inventory.
            </p>
        `;

        return;
    }


    try {

        const response =
            await fetch(
                `${API_URL}/inventory/${phcId}`
            );


        const inventory =
            await response.json();


        if (inventory.length === 0) {

            inventoryContainer.innerHTML = `
                <p class="message">
                    No inventory available for this PHC.
                </p>
            `;

            return;
        }


        inventoryContainer.innerHTML = `
            <div class="inventory-grid">

                ${inventory.map(item => {

                    let statusClass = "";

                    if (item.status === "AVAILABLE") {

                        statusClass = "available";

                    }
                    else if (item.status === "LOW_STOCK") {

                        statusClass = "low-stock";

                    }
                    else {

                        statusClass = "out-of-stock";

                    }


                    return `

                        <div class="medicine-card">

    <h3>
        ${item.medicine_name}
    </h3>

    <div class="quantity">
        ${item.quantity}
    </div>

    <p>
        Minimum Stock:
        ${item.minimum_stock}
    </p>

    <br>

    <span class="status ${statusClass}">
        ${item.status}
    </span>

    ${
        item.status === "OUT_OF_STOCK"
        ?
        `
        <br><br>

        <button
            onclick="findNearbyPHC(
                ${item.phc_id},
                ${item.medicine_id}
            )"
        >
            Find Nearby PHC
        </button>
        `
        :
        ""
    }

</div>

                    `;

                }).join("")}

            </div>
        `;

    }

    catch (error) {

        console.error(
            "Error loading inventory:",
            error
        );

        inventoryContainer.innerHTML = `
            <p class="message">
                Unable to load inventory.
            </p>
        `;

    }

}


// --------------------------------------------------
// PHC CHANGE EVENT
// --------------------------------------------------

phcSelect.addEventListener(
    "change",
    function () {

        const phcId =
            this.value;

        loadInventory(phcId);

    }
);


// --------------------------------------------------
// START APPLICATION
// --------------------------------------------------

loadPHCs();

// --------------------------------------------------
// PRESCRIPTION UPLOAD
// --------------------------------------------------

const prescriptionForm =
    document.getElementById("prescriptionForm");

const prescriptionFile =
    document.getElementById("prescriptionFile");

const uploadResult =
    document.getElementById("uploadResult");


prescriptionForm.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();


        const file =
            prescriptionFile.files[0];


        if (!file) {

            uploadResult.innerHTML =
                "Please select a prescription.";

            return;
        }


        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );


        try {

            uploadResult.innerHTML =
                "Uploading...";


            const response =
                await fetch(
                    `${API_URL}/prescription/upload`,
                    {
                        method: "POST",
                        body: formData
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                uploadResult.innerHTML =
                    data.detail;

                return;
            }


            uploadResult.innerHTML =
                `Prescription uploaded successfully: 
                 ${data.filename}`;


        }

        catch (error) {

            console.error(error);

            uploadResult.innerHTML =
                "Upload failed.";

        }

    }
);

// --------------------------------------------------
// CHECK PRESCRIPTION INVENTORY
// --------------------------------------------------

async function checkPrescriptionInventory(
    phcId,
    medicineIds
) {

    try {

        const response = await fetch(
            `${API_URL}/prescription/check/${phcId}?medicine_ids=${medicineIds}`
        );


        const data = await response.json();


        if (!response.ok) {

            console.error(data);

            return;

        }


        const result =
            document.getElementById(
                "prescriptionResult"
            );


        result.innerHTML = `
            <h3>
                Prescription Check Result
            </h3>

            ${data.medicines.map(item => `

                <div class="medicine-card">

                    <h3>
                        ${item.medicine_name}
                    </h3>

                    <p>
                        Quantity:
                        ${item.quantity}
                    </p>

                    <p>
                        Status:
                        <strong>
                            ${item.status}
                        </strong>
                    </p>

                </div>

            `).join("")}
        `;

    }

    catch (error) {

        console.error(
            "Inventory check error:",
            error
        );

    }

}

// --------------------------------------------------
// FIND NEARBY PHC
// --------------------------------------------------

async function findNearbyPHC(
    phcId,
    medicineId
) {

    try {

        const response = await fetch(
            `${API_URL}/nearby-phcs/${phcId}?medicine_id=${medicineId}`
        );


        const data = await response.json();


        if (!response.ok) {

            alert(data.detail);

            return;
        }


        if (data.nearby_phcs.length === 0) {

            alert(
                "No nearby PHC has this medicine."
            );

            return;
        }


        let message =
            `Nearby PHCs with ${data.medicine_name}:\n\n`;


        data.nearby_phcs.forEach(phc => {

            message +=
                `${phc.phc_name}\n` +
                `Available: ${phc.available_quantity}\n` +
                `Transferable: ${phc.transferable_quantity}\n\n`;

        });


        alert(message);

    }

    catch (error) {

        console.error(error);

        alert(
            "Unable to find nearby PHCs."
        );

    }

}

async function loadForecast() {

    const phcId = phcSelect.value;

    const medicineId =
        document.getElementById(
            "forecastMedicine"
        ).value;

    const forecastResult =
        document.getElementById(
            "forecastResult"
        );

    if (!phcId) {

        alert("Please select a PHC first.");

        return;
    }

    if (!medicineId) {

        alert("Please select a medicine.");

        return;
    }

    forecastResult.innerHTML = `
        <p class="message">
            Generating AI forecast...
        </p>
    `;

    try {

        const response = await fetch(
            `${API_URL}/ml-demand-forecast/${phcId}?medicine_id=${medicineId}`
        );

        const data = await response.json();

        if (!response.ok) {

            forecastResult.innerHTML = `
                <p class="message">
                    ${data.detail || "Unable to generate forecast."}
                </p>
            `;

            return;
        }

        if (data.message) {

            forecastResult.innerHTML = `
                <p class="message">
                    ${data.message}
                </p>
            `;

            return;
        }

        let warningClass = "forecast-safe";

        if (
            data.warning.includes("CRITICAL")
        ) {

            warningClass = "forecast-critical";

        } else if (
            data.warning.includes("HIGH RISK")
        ) {

            warningClass = "forecast-high";

        } else if (
            data.warning.includes("WARNING")
        ) {

            warningClass = "forecast-warning";
        }

        forecastResult.innerHTML = `

            <div class="forecast-card">

                <h3>
                    ${data.medicine_name}
                </h3>

                <p>
                    PHC:
                    <strong>
                        ${data.phc_name}
                    </strong>
                </p>

                <div class="forecast-stats">

                    <div>
                        <span>Current Stock</span>
                        <strong>
                            ${data.current_stock}
                        </strong>
                    </div>

                    <div>
                        <span>Predicted Daily Demand</span>
                        <strong>
                            ${data.average_predicted_daily_demand}
                        </strong>
                    </div>

                    <div>
                        <span>Days Remaining</span>
                        <strong>
                            ${
                                data.estimated_days_remaining !== null
                                ? data.estimated_days_remaining
                                : "N/A"
                            }
                        </strong>
                    </div>

                </div>

                <h4>
                    Next 7 Days Prediction
                </h4>

                <div class="prediction-grid">

                    ${data.predicted_next_7_days
                        .map(
                            (value, index) => `
                                <div class="prediction-day">

                                    <span>
                                        Day ${index + 1}
                                    </span>

                                    <strong>
                                        ${value}
                                    </strong>

                                    <small>
                                        patients
                                    </small>

                                </div>
                            `
                        )
                        .join("")
                    }

                </div>

                <div class="forecast-warning ${warningClass}">
                    ${data.warning}
                </div>

            </div>
        `;

    } catch (error) {

        console.error(error);

        forecastResult.innerHTML = `
            <p class="message">
                Unable to connect to backend.
            </p>
        `;
    }
}

async function loadNationalDashboard() {

    const container =
        document.getElementById(
            "nationalDashboard"
        );

    container.innerHTML = `
        <p class="message">
            Loading national dashboard...
        </p>
    `;

    try {

        const response = await fetch(
            `${API_URL}/national-dashboard`
        );

        const data = await response.json();

        if (!response.ok) {

            container.innerHTML = `
                <p class="message">
                    Unable to load dashboard.
                </p>
            `;

            return;
        }

        container.innerHTML = `

            <div class="national-grid">

                <div class="national-card">
                    <span>Total PHCs</span>
                    <strong>
                        ${data.network_summary.total_phcs}
                    </strong>
                </div>

                <div class="national-card">
                    <span>Total Medicines</span>
                    <strong>
                        ${data.network_summary.total_medicines}
                    </strong>
                </div>

                <div class="national-card">
                    <span>Total Stock Units</span>
                    <strong>
                        ${data.network_summary.total_stock_units}
                    </strong>
                </div>

                <div class="national-card">
                    <span>Patient Visits</span>
                    <strong>
                        ${data.network_summary.total_patient_visits}
                    </strong>
                </div>

                <div class="national-card">
                    <span>Out of Stock</span>
                    <strong>
                        ${data.medicine_status.out_of_stock}
                    </strong>
                </div>

                <div class="national-card">
                    <span>Low Stock</span>
                    <strong>
                        ${data.medicine_status.low_stock}
                    </strong>
                </div>

                <div class="national-card">
                    <span>Pending Transfers</span>
                    <strong>
                        ${data.operations.pending_transfers}
                    </strong>
                </div>

                <div class="national-card">
                    <span>Supplier Alerts</span>
                    <strong>
                        ${data.operations.pending_supplier_alerts}
                    </strong>
                </div>

            </div>
        `;

    } catch (error) {

        console.error(error);

        container.innerHTML = `
            <p class="message">
                Backend connection failed.
            </p>
        `;
    }
}

async function loadSystemStatus() {

    const container =
        document.getElementById(
            "systemStatus"
        );

    try {

        const response = await fetch(
            `${API_URL}/system-status`
        );

        const data = await response.json();

        container.innerHTML = `

            <div class="system-status-card">

                <h3>
                    ${data.system}
                </h3>

                <p>
                    Status:
                    <strong>
                        ${data.status}
                    </strong>
                </p>

                <div class="system-stats">

                    <div>
                        PHCs
                        <strong>
                            ${data.phcs}
                        </strong>
                    </div>

                    <div>
                        Medicines
                        <strong>
                            ${data.medicines}
                        </strong>
                    </div>

                    <div>
                        Inventory Records
                        <strong>
                            ${data.inventory_records}
                        </strong>
                    </div>

                    <div>
                        Transfer Requests
                        <strong>
                            ${data.transfer_requests}
                        </strong>
                    </div>

                    <div>
                        Supplier Alerts
                        <strong>
                            ${data.supplier_alerts}
                        </strong>
                    </div>

                    <div>
                        Patient Records
                        <strong>
                            ${data.patient_visit_records}
                        </strong>
                    </div>

                </div>

            </div>
        `;

    } catch (error) {

        console.error(error);

        container.innerHTML = `
            <p>
                Backend is not running.
            </p>
        `;
    }
}

async function testBackendConnection() {
    try {
        const response = await fetch(`${API_URL}/health`);

        if (!response.ok) {
            throw new Error("Backend response error");
        }

        const data = await response.json();

        console.log("Backend connected successfully!");
        console.log(data);

    } catch (error) {
        console.error("Backend connection failed:", error);
    }
}

testBackendConnection();