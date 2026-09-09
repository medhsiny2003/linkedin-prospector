// Mock Data for demonstration
let prospectsData = [];
let isRunning = false;
let mockInterval = null;

// DOM Elements
const views = document.querySelectorAll('.view-section');
const navLinks = document.querySelectorAll('.nav-menu a');
const tbody = document.getElementById('prospects-body');

// Navigation
navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        navLinks.forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        const viewId = link.getAttribute('data-view');
        views.forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${viewId}`).classList.add('active');
    });
});

// Settings & LocalStorage
const settingsForm = document.getElementById('settings-form');
const apiKeyInput = document.getElementById('setting-api-key');
const delayInput = document.getElementById('setting-delay');

function loadSettings() {
    const saved = localStorage.getItem('prospector_settings');
    if (saved) {
        const settings = JSON.parse(saved);
        apiKeyInput.value = settings.apiKey || '';
        delayInput.value = settings.delay || 5;
    }
}

settingsForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const settings = {
        apiKey: apiKeyInput.value,
        delay: delayInput.value
    };
    localStorage.setItem('prospector_settings', JSON.stringify(settings));
    alert('Settings saved!');
});

// Filters
const searchInput = document.getElementById('search-input');
const companyFilter = document.getElementById('filter-company');
const mxFilter = document.getElementById('filter-mx');
const scoreFilter = document.getElementById('filter-score');
const scoreVal = document.getElementById('score-val');

function renderTable() {
    const searchTerm = searchInput.value.toLowerCase();
    const company = companyFilter.value;
    const mxStatus = mxFilter.value;
    const minScore = parseInt(scoreFilter.value, 10);

    const filtered = prospectsData.filter(p => {
        const matchSearch = p.name.toLowerCase().includes(searchTerm) || p.title.toLowerCase().includes(searchTerm);
        const matchCompany = company === '' || p.company === company;
        const matchMx = mxStatus === '' || p.mx === mxStatus;
        const matchScore = p.score >= minScore;
        return matchSearch && matchCompany && matchMx && matchScore;
    });

    tbody.innerHTML = '';
    filtered.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${p.name}</td>
            <td>${p.title}</td>
            <td>${p.company}</td>
            <td>${p.email}</td>
            <td>${p.score}%</td>
            <td><span class="badge ${p.mx === 'valid' ? 'badge-success' : 'badge-danger'}">${p.mx.toUpperCase()}</span></td>
        `;
        tbody.appendChild(tr);
    });

    updateDashboard(filtered);
}

// Controls
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');

document.getElementById('btn-start').addEventListener('click', () => {
    if(isRunning) return;
    isRunning = true;
    statusDot.className = 'dot active';
    statusText.textContent = 'Running';
    // Mock simulation
    mockInterval = setInterval(simulateIncomingData, 2000);
});

document.getElementById('btn-pause').addEventListener('click', () => {
    isRunning = false;
    statusDot.className = 'dot offline';
    statusText.textContent = 'Paused';
    clearInterval(mockInterval);
});

document.getElementById('btn-stop').addEventListener('click', () => {
    isRunning = false;
    statusDot.className = 'dot offline';
    statusText.textContent = 'Stopped';
    clearInterval(mockInterval);
    // In real app, might call backend to stop process
});

document.getElementById('btn-dl-config').addEventListener('click', () => {
    const config = localStorage.getItem('prospector_settings') || '{}';
    const blob = new Blob([config], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'config.json';
    a.click();
});

document.getElementById('btn-open-folder').addEventListener('click', () => {
    alert("In a real desktop environment, this would trigger an IPC call to open the output directory.");
});

// Simulation logic
const mockCompanies = ["TechCorp", "Innovate LLC", "Global Solutions", "WebDev Studios"];
const mockNames = ["John Doe", "Jane Smith", "Mike Johnson", "Sarah Williams"];
function simulateIncomingData() {
    const newProspect = {
        name: mockNames[Math.floor(Math.random() * mockNames.length)],
        title: "Software Engineer",
        company: mockCompanies[Math.floor(Math.random() * mockCompanies.length)],
        email: `contact${Math.floor(Math.random() * 1000)}@example.com`,
        score: Math.floor(Math.random() * 41) + 60, // 60-100
        mx: Math.random() > 0.3 ? 'valid' : 'invalid'
    };
    prospectsData.push(newProspect);
    
    // Update company dropdown
    if(!Array.from(companyFilter.options).some(opt => opt.value === newProspect.company)) {
        const opt = document.createElement('option');
        opt.value = newProspect.company;
        opt.textContent = newProspect.company;
        companyFilter.appendChild(opt);
    }
    
    renderTable();
}

function updateDashboard(dataToCalculate = prospectsData) {
    document.getElementById('kpi-total').textContent = prospectsData.length;
    
    if(prospectsData.length > 0) {
        const avg = prospectsData.reduce((acc, curr) => acc + curr.score, 0) / prospectsData.length;
        document.getElementById('kpi-score').textContent = `${Math.round(avg)}%`;
        
        const validMx = prospectsData.filter(p => p.mx === 'valid').length;
        document.getElementById('kpi-mx').textContent = `${Math.round((validMx / prospectsData.length) * 100)}%`;
        
        const uniqueCompanies = new Set(prospectsData.map(p => p.company)).size;
        document.getElementById('kpi-companies').textContent = uniqueCompanies;

        // Update chart
        const chartBar = document.querySelector('.css-bar-chart .bar');
        const progress = Math.min((prospectsData.length / 50) * 100, 100); // Mock progress towards 50
        chartBar.style.height = `${progress}%`;
        chartBar.setAttribute('data-label', `${Math.round(progress)}%`);
    }
}

// Event Listeners for Filters
searchInput.addEventListener('input', renderTable);
companyFilter.addEventListener('change', renderTable);
mxFilter.addEventListener('change', renderTable);
scoreFilter.addEventListener('input', (e) => {
    scoreVal.textContent = e.target.value;
    renderTable();
});

// Exports
function downloadFile(content, fileName, mimeType) {
    const a = document.createElement('a');
    const blob = new Blob([content], {type: mimeType});
    a.href = URL.createObjectURL(blob);
    a.download = fileName;
    a.click();
}

document.getElementById('btn-export-csv').addEventListener('click', () => {
    if(prospectsData.length === 0) return alert('No data to export');
    const headers = 'Name,Title,Company,Email,Score,MX\n';
    const csv = prospectsData.map(p => `${p.name},${p.title},${p.company},${p.email},${p.score},${p.mx}`).join('\n');
    downloadFile(headers + csv, 'prospects.csv', 'text/csv');
});

document.getElementById('btn-export-json').addEventListener('click', () => {
    if(prospectsData.length === 0) return alert('No data to export');
    downloadFile(JSON.stringify(prospectsData, null, 2), 'prospects.json', 'application/json');
});

document.getElementById('btn-export-excel').addEventListener('click', () => {
    if(prospectsData.length === 0) return alert('No data to export');
    if(typeof XLSX !== 'undefined') {
        const ws = XLSX.utils.json_to_sheet(prospectsData);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Prospects");
        XLSX.writeFile(wb, "prospects.xlsx");
    } else {
        alert("XLSX library not loaded");
    }
});

document.getElementById('btn-copy-valid').addEventListener('click', () => {
    const validEmails = prospectsData.filter(p => p.mx === 'valid').map(p => p.email).join('\n');
    if(!validEmails) return alert('No valid emails to copy');
    navigator.clipboard.writeText(validEmails).then(() => {
        alert('Copied valid emails to clipboard!');
    });
});

// Init
loadSettings();
renderTable();
