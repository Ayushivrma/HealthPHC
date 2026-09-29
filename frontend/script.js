// Backend URL
//const API_URL = "http://127.0.0.1:8000";
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
let medicineSearchTimeout;

const medicineSearch =
    document.getElementById("medicineSearch");

const medicineSelect =
    document.getElementById("forecastMedicine");

medicineSearch.addEventListener("input", function () {

    clearTimeout(medicineSearchTimeout);

    const query = medicineSearch.value.trim().toLowerCase();

    medicineSelect.innerHTML =
        '<option value="">Select Medicine</option>';

    if (query.length < 2) {
        return;
    }

    medicineSearchTimeout = setTimeout(async function () {

        try {

            // Get medicines available in our PHC database
            const localResponse =
                await fetch(`${API_URL}/medicines`);

            const localMedicines =
                await localResponse.json();

            // Find matching local medicines
            const matches =
                localMedicines.filter(medicine =>
                    medicine.name
                        .toLowerCase()
                        .includes(query)
                );

            matches.forEach(medicine => {

                const option =
                    document.createElement("option");

                // IMPORTANT:
                // Use local database medicine ID
                option.value = medicine.id;

                option.textContent =
                    medicine.name;

                medicineSelect.appendChild(option);

            });

            // If no local medicine found,
            // show message instead of sending RxNorm ID
            if (matches.length === 0) {

                const option =
                    document.createElement("option");

                option.value = "";

                option.textContent =
                    "Medicine not available in PHC database";

                medicineSelect.appendChild(option);
            }

        }

        catch (error) {

            console.error(
                "Error searching medicines:",
                error
            );

        }

    }, 300);
});

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


// ========================================================
// PROFILE DROPDOWN + PROFILE UPDATE
// ========================================================

document.addEventListener("DOMContentLoaded", function () {

    // ---------- ELEMENTS ----------

    const profileButton = document.getElementById("profileButton");
    const profileDropdown = document.getElementById("profileDropdown");
    const profileWrapper = document.querySelector(".user-profile-wrapper");

    const viewProfileBtn = document.getElementById("viewProfileBtn");
    const editProfileBtn = document.getElementById("editProfileBtn");
    const anotherAccountBtn = document.getElementById("anotherAccountBtn");
    const logoutBtn = document.getElementById("logoutBtn");

    const profileModal = document.getElementById("profileModal");
    const closeProfileModal = document.getElementById("closeProfileModal");
    const cancelProfileBtn = document.getElementById("cancelProfileBtn");
    const saveProfileBtn = document.getElementById("saveProfileBtn");

    const profileName = document.getElementById("profileName");
    const profileEmail = document.getElementById("profileEmail");
    const profilePhone = document.getElementById("profilePhone");
    const profileRole = document.getElementById("profileRole");

    const profilePictureInput =
        document.getElementById("profilePictureInput");

    const largeProfileAvatar =
        document.getElementById("largeProfileAvatar");

    const dropdownAvatar =
        document.getElementById("dropdownAvatar");

    // ---------- PROFILE DATA ----------

    function getProfileData() {

        const savedProfile =
            localStorage.getItem("healthresq_profile");

        if (savedProfile) {
            try {
                return JSON.parse(savedProfile);
            } catch (error) {
                console.error("Profile data error:", error);
            }
        }

        return {
            name: localStorage.getItem("healthresq_user") || "User",
            email: "",
            phone: "",
            role: "Administrator",
            picture: ""
        };
    }


    // ---------- UPDATE DASHBOARD PROFILE ----------

    function updateProfileUI() {

        const profile = getProfileData();

        const loggedInName =
            document.getElementById("loggedInName");

        const loggedInEmail =
            document.getElementById("loggedInEmail");

        const dropdownName =
            document.getElementById("dropdownName");

        const dropdownEmail =
            document.getElementById("dropdownEmail");

        const userAvatar =
            document.getElementById("userAvatar");


        if (loggedInName) {
            loggedInName.textContent = profile.name;
        }

        if (loggedInEmail) {
            loggedInEmail.textContent =
                profile.email || profile.role;
        }

        if (dropdownName) {
            dropdownName.textContent = profile.name;
        }

        if (dropdownEmail) {
            dropdownEmail.textContent =
                profile.email || profile.role;
        }


        // Initials
        const initials = profile.name
            .split(" ")
            .map(word => word.charAt(0))
            .join("")
            .substring(0, 2)
            .toUpperCase();


        if (profile.picture) {

            const imageHTML =
                `<img src="${profile.picture}" alt="Profile">`;

            if (userAvatar) {
                userAvatar.innerHTML = imageHTML;
            }

            if (dropdownAvatar) {
                dropdownAvatar.innerHTML = imageHTML;
            }

            if (largeProfileAvatar) {
                largeProfileAvatar.innerHTML = imageHTML;
            }

        } else {

            if (userAvatar) {
                userAvatar.textContent = initials;
            }

            if (dropdownAvatar) {
                dropdownAvatar.textContent = initials;
            }

            if (largeProfileAvatar) {
                largeProfileAvatar.textContent = initials;
            }
        }
    }


    // ====================================================
    // PROFILE DROPDOWN
    // ====================================================

    if (profileButton) {

        profileButton.addEventListener("click", function (event) {

            event.preventDefault();
            event.stopPropagation();

            profileDropdown.classList.toggle("hidden");

            if (profileWrapper) {
                profileWrapper.classList.toggle("active");
            }
        });
    }


    // Close dropdown when clicking outside

    document.addEventListener("click", function (event) {

        if (
            profileWrapper &&
            !profileWrapper.contains(event.target)
        ) {

            profileDropdown.classList.add("hidden");

            profileWrapper.classList.remove("active");
        }
    });


    // ====================================================
    // OPEN PROFILE MODAL
    // ====================================================

    function openProfileModal() {

        const profile = getProfileData();

        profileName.value = profile.name || "";
        profileEmail.value = profile.email || "";
        profilePhone.value = profile.phone || "";
        profileRole.value =
            profile.role || "Administrator";

        profileModal.classList.remove("hidden");

        profileDropdown.classList.add("hidden");

        if (profileWrapper) {
            profileWrapper.classList.remove("active");
        }

        updateProfileUI();
    }


    // Edit Profile

    if (editProfileBtn) {

        editProfileBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                openProfileModal();
            }
        );
    }


    // My Profile

    if (viewProfileBtn) {

        viewProfileBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                openProfileModal();
            }
        );
    }


    // ====================================================
    // PROFILE PHOTO
    // ====================================================

    if (profilePictureInput) {

        profilePictureInput.addEventListener(
            "change",
            function () {

                const file = this.files[0];

                if (!file) return;

                if (!file.type.startsWith("image/")) {

                    alert("Please select an image file.");

                    return;
                }

                const reader = new FileReader();

                reader.onload = function (event) {

                    const image =
                        event.target.result;

                    largeProfileAvatar.innerHTML =
                        `<img src="${image}" alt="Profile">`;

                    const profile = getProfileData();

                    profile.picture = image;

                    localStorage.setItem(
                        "healthresq_profile",
                        JSON.stringify(profile)
                    );
                };

                reader.readAsDataURL(file);
            }
        );
    }


    // ====================================================
    // SAVE CHANGES
    // ====================================================

    if (saveProfileBtn) {

        saveProfileBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                const name =
                    profileName.value.trim();

                const email =
                    profileEmail.value.trim();

                const phone =
                    profilePhone.value.trim();

                const role =
                    profileRole.value;


                // Only NAME is required
                // Photo is NOT required

                if (!name) {

                    alert("Please enter your name.");

                    profileName.focus();

                    return;
                }


                const oldProfile =
                    getProfileData();


                const updatedProfile = {

                    name: name,

                    email: email,

                    phone: phone,

                    role: role,

                    picture:
                        oldProfile.picture || ""
                };


                // Save profile

                localStorage.setItem(
                    "healthresq_profile",
                    JSON.stringify(updatedProfile)
                );


                // Update logged-in user

                localStorage.setItem(
                    "healthresq_user",
                    name
                );


                // Update dashboard

                updateProfileUI();


                // Close modal

                profileModal.classList.add("hidden");


                alert("Profile updated successfully!");
            }
        );
    }


    // ====================================================
    // CLOSE WITH X
    // ====================================================

    if (closeProfileModal) {

        closeProfileModal.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                profileModal.classList.add("hidden");
            }
        );
    }


    // ====================================================
    // CANCEL BUTTON
    // ====================================================

    if (cancelProfileBtn) {

        cancelProfileBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                profileModal.classList.add("hidden");
            }
        );
    }


    // ====================================================
    // CLICK OUTSIDE MODAL
    // ====================================================

    if (profileModal) {

        profileModal.addEventListener(
            "click",
            function (event) {

                if (event.target === profileModal) {

                    profileModal.classList.add("hidden");
                }
            }
        );
    }


    // ====================================================
    // LOGIN WITH ANOTHER ACCOUNT
    // ====================================================

    if (anotherAccountBtn) {

        anotherAccountBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                localStorage.removeItem(
                    "healthresq_user"
                );

                localStorage.removeItem(
                    "healthresq_profile"
                );

                window.location.reload();
            }
        );
    }


    // ====================================================
    // LOGOUT
    // ====================================================

    if (logoutBtn) {

        logoutBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                const confirmLogout =
                    confirm(
                        "Are you sure you want to logout?"
                    );

                if (!confirmLogout) return;

                localStorage.removeItem(
                    "healthresq_user"
                );

                window.location.reload();
            }
        );
    }


    // ====================================================
    // INITIAL PROFILE LOAD
    // ====================================================

    updateProfileUI();

});

/* ================= LOGIN FLOW ================= */

document.addEventListener("DOMContentLoaded", function () {

    const loginForm = document.getElementById("loginForm");
    const loginScreen = document.getElementById("loginScreen");
    const appContainer = document.getElementById("appContainer");
    const loginName = document.getElementById("loginName");
    const loginPassword = document.getElementById("loginPassword");
    const loginError = document.getElementById("loginError");

    if (!loginForm) return;

    loginForm.addEventListener("submit", function (event) {

        event.preventDefault();

        const name = loginName.value.trim();
        const password = loginPassword.value.trim();

        if (!name || !password) {
            loginError.textContent = "Please enter your name and password.";
            return;
        }

        // Save logged-in user
        localStorage.setItem("healthresq_user", name);

        // Hide login screen
        loginScreen.classList.add("hidden");

        // Show main dashboard
        appContainer.classList.remove("hidden");

        // Update welcome message
        const welcomeHeading = document.querySelector(".welcome h1");

        if (welcomeHeading) {
            welcomeHeading.textContent = `Welcome back, ${name}! 👋`;
        }

        // Load dashboard data
        if (typeof loadPHCs === "function") {
            loadPHCs();
        }

    });

});