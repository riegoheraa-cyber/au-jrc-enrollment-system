const API_BASE = "https://ommatophorous-ryder-prepotently.ngrok-free.dev"; // use same-origin backend

// ---------- BASIC PAGE SWITCHING ----------
const pages = document.querySelectorAll('.page');
const navButtons = document.querySelectorAll('[data-target]');

function showPage(id) {
    pages.forEach(p => p.classList.remove('active'));
    document.getElementById(id).classList.add('active');
}

navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-target');
        showPage(target);
    });
});

// ---------- SIMPLE STORAGE HELPERS (localStorage) ----------
function getStored(key, fallback) {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
}

function setStored(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
}

// ---------- DEFAULT CONTENT ----------
const defaultAbout = "Default About Us text for AU-JRC. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus at posuere felis, a molestie lectus. Fusce id dapibus nisi. Nullam lacus nulla, dignissim a ullamcorper vel, accumsan non augue. Suspendisse potenti. Nam sed lorem sem. Cras ut sem porta, porta libero id, mattis lectus. Aliquam et porttitor lorem. Sed finibus tortor nec gravida euismod. Morbi quis odio in nisi sagittis maximus in sed eros. Vestibulum at orci metus. Nam ac neque ultricies, faucibus lacus eget, semper dolor. Nam nec mi neque. Etiam pretium blandit tempus. Nulla facilisi. Aenean mollis cursus pellentesque. ";
const defaultPrivacy = "Default Privacy Notice. Data is used only for Reservation. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus at posuere felis, a molestie lectus. Fusce id dapibus nisi. Nullam lacus nulla, dignissim a ullamcorper vel, accumsan non augue. Suspendisse potenti. Nam sed lorem sem. Cras ut sem porta, porta libero id, mattis lectus. Aliquam et porttitor lorem. Sed finibus tortor nec gravida euismod. Morbi quis odio in nisi sagittis maximus in sed eros. Vestibulum at orci metus. Nam ac neque ultricies, faucibus lacus eget, semper dolor. Nam nec mi neque. Etiam pretium blandit tempus. Nulla facilisi. Aenean mollis cursus pellentesque. ";

// show About + Privacy text on public pages and in admin editor
function initContent() {
    const aboutText = getStored('aboutText', defaultAbout);
    const privacyText = getStored('privacyText', defaultPrivacy);

    document.getElementById('public-about-text').textContent = aboutText;
    document.getElementById('public-privacy-text').textContent = privacyText;

    const aboutEditor = document.getElementById('about-editor');
    const privacyEditor = document.getElementById('privacy-editor');
    if (aboutEditor) aboutEditor.value = aboutText;
    if (privacyEditor) privacyEditor.value = privacyText;
}

// ---------- PRIVACY -> Reservation ----------
// document.getElementById('agree-privacy-btn')
//     .addEventListener('click', () => showPage('Reservation-page'));

// ---------- Reservation FORM (SAVE ENROLLEE) ----------
const ReservationForm = document.getElementById('Reservation-form');
const ReservationMsg = document.getElementById('Reservation-message');

if (ReservationForm) {
    ReservationForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const data = new FormData(ReservationForm);
        const fullName = [data.get('surname'), data.get('givenName'), data.get('middleName')]
            .map(v => (v || '').trim())
            .filter(Boolean)
            .join(' ');

        const track = data.get('track');
        const strand = track === 'Academic Track' ? data.get('academicStrand') : (track === 'TVL Track' ? 'TVL' : '');

        const reservation = {
            fullName,
            lrn: data.get('lrn'),
            dob: data.get('dob'),
            pob: data.get('pob'),
            address: data.get('address'),
            sex: data.get('sex'),
            nationality: data.get('nationality'),
            email: data.get('email'),
            contactNo: data.get('contactNo'),

            jhsGraduated: data.get('jhsGraduated'),
            dateGraduation: data.get('dateGraduation'),

            gradeLevel: data.get('gradeLevel'),
            strand,
            tvlSpec: data.get('tvlSpec'),
            generalAve: data.get('generalAve'),

            medicalConditions: data.getAll('medical[]'),
            medicalOther: data.get('medicalOther'),
            howSupported: data.get('howSupported'),

            guardianName: data.get('guardianName'),
            guardianRelationship: data.get('relationship'),
            guardianOccupation: data.get('occupation'),
            telNo: data.get('telNo'),
            cellphoneNo: data.get('cellphoneNo'),

            credentialsSubmitted: data.get('credentialsSubmitted')
        };

        const Reservations = getStored('Reservations', []);
        Reservations.push({ ...reservation, submittedAt: new Date().toISOString() });
        setStored('Reservations', Reservations);

        try {
            const res = await fetch(`${API_BASE}/api/enroll`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(reservation),
            });

            const payload = await res.json();

            if (!res.ok || !payload.ok) {
                throw new Error(payload.error || "Submit failed");
            }

            alert(`Submitted! Application ID: ${payload.application_id}`);
            e.target.reset();
            if (ReservationMsg) ReservationMsg.textContent = "Reservation submitted successfully.";
        } catch (err) {
            alert("Error: " + err.message);
            if (ReservationMsg) ReservationMsg.textContent = "Submission failed.";
        }
    });
}

// ---------- ADMIN LOGIN ----------
// const adminLoginForm = document.getElementById('admin-login-form');
// const adminLoginMsg = document.getElementById('admin-login-message');

// adminLoginForm.addEventListener('submit', function (e) {
//     e.preventDefault();
//     const user = document.getElementById('admin-username').value.trim();
//     const pass = document.getElementById('admin-password').value.trim();

//     if (user === "admin" && pass === "admin123") {
//         adminLoginMsg.textContent = "";
//         showPage('admin-dashboard-page');
//         initDashboard();
//     } else {
//         adminLoginMsg.textContent = "Invalid account.";
//     }
// });

// document.getElementById('logout-btn')
//     .addEventListener('click', () => showPage('home-page'));

// ---------- MANAGE Reservations (TABLE + FILTER BY MONTH/YEAR) ----------
const tableBody = document.querySelector('#Reservations-table tbody');
const filterMonth = document.getElementById('filter-month');
const filterYear = document.getElementById('filter-year');

function loadFilterOptions() {
    const Reservations = getStored('Reservations', []);
    const months = new Set();
    const years = new Set();

    Reservations.forEach(e => {
        const d = new Date(e.submittedAt);
        months.add(d.getMonth() + 1);
        years.add(d.getFullYear());
    });

    filterMonth.innerHTML = '<option value="">All</option>';
    months.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m.toString().padStart(2, '0');
        filterMonth.appendChild(opt);
    });

    filterYear.innerHTML = '<option value="">All</option>';
    years.forEach(y => {
        const opt = document.createElement('option');
        opt.value = y;
        opt.textContent = y;
        filterYear.appendChild(opt);
    });
}

function renderReservationsTable() {
    const Reservations = getStored('Reservations', []);
    const month = filterMonth.value;
    const year = filterYear.value;

    tableBody.innerHTML = "";

    Reservations.forEach(e => {
        const d = new Date(e.submittedAt);
        const m = d.getMonth() + 1;
        const y = d.getFullYear();

        if (month && Number(month) !== m) return;
        if (year && Number(year) !== y) return;

        const tr = document.createElement('tr');
        tr.innerHTML = `
      <td>${d.toLocaleDateString()}</td>
      <td>${e.fullName}</td>
      <td>${e.gradeLevel}</td>
      <td>${e.strand}</td>
    `;
        tableBody.appendChild(tr);
    });
}

// document.getElementById('filter-Reservations-btn')
//     .addEventListener('click', renderReservationsTable);

// ---------- FACILITIES (ADD + DISPLAY) ----------
// const facilityForm = document.getElementById('facility-form');
// const adminFacilitiesList = document.getElementById('admin-facilities-list');
// const publicFacilitiesList = document.getElementById('public-facilities-list');

function renderFacilities() {
    const facilities = getStored('facilities', []);
    adminFacilitiesList.innerHTML = "";
    publicFacilitiesList.innerHTML = "";

    facilities.forEach(f => {
        const li1 = document.createElement('li');
        li1.textContent = f.name + " - " + f.purpose;
        adminFacilitiesList.appendChild(li1);

        const li2 = document.createElement('li');
        li2.textContent = f.name + ": " + f.description;
        publicFacilitiesList.appendChild(li2);
    });
}

// facilityForm.addEventListener('submit', function (e) {
//     e.preventDefault();

//     const data = new FormData(facilityForm);
//     const facility = {
//         name: data.get('facilityName'),
//         purpose: data.get('facilityPurpose'),
//         description: data.get('facilityDescription')
//     };

//     const facilities = getStored('facilities', []);
//     facilities.push(facility);
//     setStored('facilities', facilities);

//     facilityForm.reset();
//     renderFacilities();
// });
const tvlOptions = [
  "ICT",
  "Home Economics",
  "Cookery",
];

// const trackEl = document.getElementById("strand");
// const tvlWrap = document.getElementById("tvlWrap");
// const tvlSpec = document.getElementById("tvlSpec");

// function setTvlVisible(isVisible) {
//   tvlWrap.style.display = isVisible ? "block" : "none";
//   tvlSpec.required = isVisible;
//   if (!isVisible) tvlSpec.value = "";
// }

// function loadTvlOptions() {
//   tvlSpec.innerHTML = `<option value="" selected disabled>Select TVL specialization</option>`;
//   tvlOptions.forEach(opt => {
//     const o = document.createElement("option");
//     o.value = opt;
//     o.textContent = opt;
//     tvlSpec.appendChild(o);
//   });
// }

// trackEl.addEventListener("change", () => {
//   if (trackEl.value === "TVL") {
//     loadTvlOptions();
//     setTvlVisible(true);
//   } else {
//     setTvlVisible(false);
//   }
// });
// ---------- CONTENT MANAGEMENT (ABOUT + PRIVACY) ----------
// document.getElementById('save-about-btn')
//     .addEventListener('click', () => {
//         const txt = document.getElementById('about-editor').value.trim();
//         setStored('aboutText', txt || defaultAbout);
//         initContent();
//     });

// document.getElementById('save-privacy-btn')
//     .addEventListener('click', () => {
//         const txt = document.getElementById('privacy-editor').value.trim();
//         setStored('privacyText', txt || defaultPrivacy);
//         initContent();
//     });

// ---------- ADMIN DASHBOARD INIT ----------
function initDashboard() {
    // initContent();
    // loadFilterOptions();
    // renderReservationsTable();
    // renderFacilities();
}

// ---------- INITIAL APP STATE ----------
// initContent();
// renderFacilities();
// showPage('home-page');
 