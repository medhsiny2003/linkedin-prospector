class LinkedInProspector {
    constructor() {
        this.contacts = [];
        this.filteredContacts = [];
        this.currentPage = 1;
        this.rowsPerPage = 20;
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.pollInterval = null;
        this.init();
    }

    init() {
        // Form controls
        const btnGenerateConfig = document.getElementById('btn-generate-config');
        if (btnGenerateConfig) {
            btnGenerateConfig.addEventListener('click', () => this.generateConfig());
        }

        // Direct Execution Buttons
        const btnStart = document.getElementById('btn-start-scraping');
        if (btnStart) {
            btnStart.addEventListener('click', () => this.startScraping());
        }

        const btnStop = document.getElementById('btn-stop-scraping');
        if (btnStop) {
            btnStop.addEventListener('click', () => this.stopScraping());
        }

        const btnOpenFolder = document.getElementById('btn-open-folder');
        if (btnOpenFolder) {
            btnOpenFolder.addEventListener('click', () => this.openFolder());
        }

        // File upload
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');

        if (dropZone && fileInput) {
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            });
            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('dragover');
            });
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
                if (e.dataTransfer.files.length) {
                    this.handleFile(e.dataTransfer.files[0]);
                }
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) {
                    this.handleFile(e.target.files[0]);
                }
            });
        }

        // Search and Export
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.filterContacts(e.target.value));
        }

        const btnExportExcel = document.getElementById('btn-export-excel');
        if (btnExportExcel) {
            btnExportExcel.addEventListener('click', () => this.exportExcel());
        }

        const btnCopyEmails = document.getElementById('btn-copy-emails');
        if (btnCopyEmails) {
            btnCopyEmails.addEventListener('click', () => this.copyEmails());
        }

        // Table sorting
        document.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', () => this.sortBy(th.dataset.sort));
        });

        // Pagination
        const btnPrev = document.getElementById('btn-prev-page');
        const btnNext = document.getElementById('btn-next-page');
        
        if (btnPrev) {
            btnPrev.addEventListener('click', () => {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.renderTable();
                }
            });
        }
        
        if (btnNext) {
            btnNext.addEventListener('click', () => {
                const totalPages = Math.ceil(this.filteredContacts.length / this.rowsPerPage);
                if (this.currentPage < totalPages) {
                    this.currentPage++;
                    this.renderTable();
                }
            });
        }

        // Auto load existing database results if running on local server
        this.loadExistingResults();
    }

    async loadExistingResults() {
        try {
            const res = await fetch('/api/results');
            if (res.ok) {
                const data = await res.json();
                if (data.contacts && data.contacts.length > 0) {
                    this.contacts = data.contacts.map(c => ({
                        id: c.id,
                        first_name: c.first_name,
                        last_name: c.last_name,
                        position: c.title,
                        company: c.company,
                        email: c.email,
                        score: c.confidence_score,
                        mx_status: c.mx_status,
                        mx_server: c.mx_active ? 'Actif' : 'Inconnu',
                        linkedin_url: c.linkedin_url,
                        date: c.extraction_date
                    }));
                    this.filteredContacts = [...this.contacts];
                    document.getElementById('results-container').classList.remove('hidden');
                    document.getElementById('dashboard-section').classList.remove('hidden');
                    this.renderTable();
                    this.renderDashboard();
                }
            }
        } catch (e) {
            // Static mode (GitHub Pages), ignore
        }
    }

    async startScraping() {
        const companies = document.getElementById('companies').value.split('\n').map(s => s.trim()).filter(s => s);
        const keywords = document.getElementById('keywords').value.split('\n').map(s => s.trim()).filter(s => s);
        const location = document.getElementById('location').value.trim();
        const max_results = parseInt(document.getElementById('max_results').value, 10) || 50;
        const email_level = document.getElementById('email_level').value;
        const enable_smtp_check = document.getElementById('smtp_check').checked;

        if (companies.length === 0 || keywords.length === 0) {
            this.showNotification("Veuillez remplir au moins une entreprise et un mot-clé.", "error");
            return;
        }

        const config = {
            companies,
            keywords,
            location: location || "France",
            max_results,
            email_level,
            enable_smtp_check
        };

        const consoleSection = document.getElementById('console-section');
        const btnStart = document.getElementById('btn-start-scraping');
        const btnStop = document.getElementById('btn-stop-scraping');
        
        consoleSection.classList.remove('hidden');
        btnStart.classList.add('hidden');
        btnStop.classList.remove('hidden');

        try {
            const res = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || "Erreur au lancement");
            }

            this.showNotification("🚀 Prospection démarrée !", "success");
            this.startPollingStatus();
        } catch (err) {
            this.showNotification(`Erreur: ${err.message}`, "error");
            btnStart.classList.remove('hidden');
            btnStop.classList.add('hidden');
        }
    }

    startPollingStatus() {
        if (this.pollInterval) clearInterval(this.pollInterval);
        
        const logsContainer = document.getElementById('live-logs');
        const statusBadge = document.getElementById('status-badge');
        const btnStart = document.getElementById('btn-start-scraping');
        const btnStop = document.getElementById('btn-stop-scraping');

        this.pollInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                if (!res.ok) return;
                
                const data = await res.json();
                
                // Update logs
                if (data.logs && data.logs.length > 0) {
                    logsContainer.innerHTML = data.logs.map(log => {
                        let color = '#a9b7d0';
                        if (log.level === 'ERROR') color = '#e74c3c';
                        else if (log.level === 'WARNING') color = '#f39c12';
                        else if (log.level === 'SUCCESS') color = '#2ecc71';
                        else if (log.message.includes('▶') || log.message.includes('🔎')) color = '#3498db';
                        return `<div style="color: ${color}; margin-bottom: 3px;">[${log.timestamp}] ${log.message}</div>`;
                    }).join('');
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                }

                // Update Status
                if (data.status === 'running') {
                    statusBadge.textContent = "⚡ En cours d'exécution";
                    statusBadge.className = "badge badge-warning";
                } else if (data.status === 'completed') {
                    statusBadge.textContent = "✅ Terminé avec succès";
                    statusBadge.className = "badge badge-success";
                    clearInterval(this.pollInterval);
                    btnStart.classList.remove('hidden');
                    btnStop.classList.add('hidden');
                    this.showNotification("Prospection terminée !", "success");
                    this.loadExistingResults();
                } else if (data.status === 'error') {
                    statusBadge.textContent = "❌ Erreur";
                    statusBadge.className = "badge badge-danger";
                    clearInterval(this.pollInterval);
                    btnStart.classList.remove('hidden');
                    btnStop.classList.add('hidden');
                } else if (data.status === 'idle') {
                    statusBadge.textContent = "Prêt";
                    statusBadge.className = "badge badge-gray";
                    clearInterval(this.pollInterval);
                    btnStart.classList.remove('hidden');
                    btnStop.classList.add('hidden');
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 1500);
    }

    async stopScraping() {
        try {
            await fetch('/api/stop', { method: 'POST' });
            this.showNotification("Arrêt demandé...", "warning");
        } catch (err) {
            this.showNotification("Erreur lors de l'arrêt", "error");
        }
    }

    async openFolder() {
        try {
            await fetch('/api/open_folder', { method: 'POST' });
            this.showNotification("Dossier des résultats ouvert !", "info");
        } catch (err) {
            this.showNotification("Impossible d'ouvrir le dossier", "error");
        }
    }

    generateConfig() {
        const companies = document.getElementById('companies').value.split('\n').map(s => s.trim()).filter(s => s);
        const keywords = document.getElementById('keywords').value.split('\n').map(s => s.trim()).filter(s => s);
        const location = document.getElementById('location').value.trim();
        const max_results_per_company = parseInt(document.getElementById('max_results').value, 10) || 50;
        const email_level = document.getElementById('email_level').value;
        const enable_smtp_check = document.getElementById('smtp_check').checked;

        if (companies.length === 0 || keywords.length === 0) {
            this.showNotification("Veuillez remplir les entreprises et les mots-clés.", "error");
            return;
        }

        const config = {
            companies,
            keywords,
            location: location || undefined,
            max_results_per_company,
            email_level,
            enable_smtp_check
        };

        const json = JSON.stringify(config, null, 2);
        this.downloadFile(json, 'config.json', 'application/json');
        this.showNotification("Fichier config.json généré !", "success");
    }

    handleFile(file) {
        if (!file.name.endsWith('.json')) {
            this.showNotification("Veuillez fournir un fichier JSON.", "error");
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                if (!Array.isArray(data)) {
                    throw new Error("Format invalide (le fichier doit être un tableau JSON)");
                }
                this.contacts = data.map(c => ({
                    id: c.id,
                    first_name: c.first_name,
                    last_name: c.last_name,
                    position: c.title || c.position,
                    company: c.company,
                    email: c.email,
                    score: c.confidence_score || c.score,
                    mx_status: c.mx_status,
                    mx_server: c.mx_active ? 'Actif' : (c.mx_server || 'Inconnu'),
                    linkedin_url: c.linkedin_url,
                    date: c.extraction_date || c.date
                }));
                this.filteredContacts = [...this.contacts];
                this.currentPage = 1;
                
                document.getElementById('results-container').classList.remove('hidden');
                document.getElementById('dashboard-section').classList.remove('hidden');
                
                this.renderTable();
                this.renderDashboard();
                this.showNotification(`${this.contacts.length} contacts chargés.`, "success");
            } catch (err) {
                this.showNotification(`Erreur lors de la lecture: ${err.message}`, "error");
            }
        };
        reader.readAsText(file);
    }

    renderTable() {
        const tbody = document.getElementById('table-body');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        const startIndex = (this.currentPage - 1) * this.rowsPerPage;
        const endIndex = Math.min(startIndex + this.rowsPerPage, this.filteredContacts.length);
        const pageData = this.filteredContacts.slice(startIndex, endIndex);
        
        pageData.forEach(c => {
            const tr = document.createElement('tr');
            
            let scoreBadge = '';
            if (c.score >= 80) scoreBadge = 'badge-success';
            else if (c.score >= 50) scoreBadge = 'badge-warning';
            else scoreBadge = 'badge-danger';

            let mxBadge = 'badge-gray';
            const status = c.mx_status ? String(c.mx_status).toLowerCase() : '';
            if (status.includes('valid')) mxBadge = 'badge-success';
            else if (status.includes('catch-all') || status.includes('catchall')) mxBadge = 'badge-warning';
            else if (status.includes('invalid') || status.includes('error')) mxBadge = 'badge-danger';

            tr.innerHTML = `
                <td>${c.id || '-'}</td>
                <td>${c.first_name || '-'}</td>
                <td>${c.last_name || '-'}</td>
                <td>${c.position || '-'}</td>
                <td>${c.company || '-'}</td>
                <td><strong>${c.email || '-'}</strong></td>
                <td><span class="badge ${scoreBadge}">${c.score || 0}%</span></td>
                <td><span class="badge ${mxBadge}">${c.mx_status || 'Unknown'}</span></td>
                <td>${c.mx_server || '-'}</td>
                <td>${c.linkedin_url ? `<a href="${c.linkedin_url}" target="_blank" style="color: #3498db; text-decoration: underline;">Voir profil</a>` : '-'}</td>
                <td>${c.date ? new Date(c.date).toLocaleDateString('fr-FR') : '-'}</td>
            `;
            tbody.appendChild(tr);
        });

        // Update pagination
        const totalPages = Math.ceil(this.filteredContacts.length / this.rowsPerPage) || 1;
        document.getElementById('page-info').textContent = `Page ${this.currentPage} / ${totalPages}`;
        document.getElementById('btn-prev-page').disabled = this.currentPage === 1;
        document.getElementById('btn-next-page').disabled = this.currentPage === totalPages;
    }

    sortBy(column) {
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }

        this.filteredContacts.sort((a, b) => {
            let valA = a[column];
            let valB = b[column];
            
            if (valA === undefined || valA === null) valA = '';
            if (valB === undefined || valB === null) valB = '';

            if (typeof valA === 'string') valA = valA.toLowerCase();
            if (typeof valB === 'string') valB = valB.toLowerCase();

            if (valA < valB) return this.sortDirection === 'asc' ? -1 : 1;
            if (valA > valB) return this.sortDirection === 'asc' ? 1 : -1;
            return 0;
        });

        this.currentPage = 1;
        this.renderTable();
    }

    filterContacts(query) {
        if (!query) {
            this.filteredContacts = [...this.contacts];
        } else {
            const q = query.toLowerCase();
            this.filteredContacts = this.contacts.filter(c => {
                return Object.values(c).some(val => 
                    val !== null && val !== undefined && String(val).toLowerCase().includes(q)
                );
            });
        }
        this.currentPage = 1;
        this.renderTable();
    }

    renderDashboard() {
        if (this.contacts.length === 0) return;

        // Total
        document.getElementById('stat-total').textContent = this.contacts.length;

        // Avg Score
        const validScores = this.contacts.filter(c => typeof c.score === 'number' && c.score > 0);
        const avgScore = validScores.length ? validScores.reduce((acc, c) => acc + c.score, 0) / validScores.length : 0;
        document.getElementById('stat-avg-score').textContent = `${Math.round(avgScore)}%`;

        // MX Valid
        const validMX = this.contacts.filter(c => c.mx_status && String(c.mx_status).toLowerCase().includes('valid'));
        const mxRate = (validMX.length / this.contacts.length) * 100;
        document.getElementById('stat-mx-valid').textContent = `${Math.round(mxRate)}%`;

        // Companies Chart
        const companies = {};
        this.contacts.forEach(c => {
            const comp = c.company || 'Autre';
            companies[comp] = (companies[comp] || 0) + 1;
        });
        
        const companyChart = document.getElementById('company-chart');
        companyChart.innerHTML = '';
        const maxCompCount = Math.max(...Object.values(companies), 1);
        
        Object.entries(companies).sort((a, b) => b[1] - a[1]).slice(0, 10).forEach(([comp, count]) => {
            const width = (count / maxCompCount) * 100;
            companyChart.innerHTML += `
                <div class="chart-bar-container">
                    <div class="chart-label" title="${comp}">${comp}</div>
                    <div class="chart-bar-wrapper">
                        <div class="chart-bar" style="width: ${width}%"></div>
                    </div>
                    <div class="chart-value">${count}</div>
                </div>
            `;
        });

        // Score Distribution
        const scores = { '>= 80': 0, '50-79': 0, '< 50': 0 };
        this.contacts.forEach(c => {
            const s = c.score || 0;
            if (s >= 80) scores['>= 80']++;
            else if (s >= 50) scores['50-79']++;
            else scores['< 50']++;
        });

        const scoreChart = document.getElementById('score-chart');
        scoreChart.innerHTML = '';
        const maxScoreCount = Math.max(...Object.values(scores), 1);

        Object.entries(scores).forEach(([label, count]) => {
            const width = (count / maxScoreCount) * 100;
            scoreChart.innerHTML += `
                <div class="chart-bar-container">
                    <div class="chart-label">${label}%</div>
                    <div class="chart-bar-wrapper">
                        <div class="chart-bar" style="width: ${width}%"></div>
                    </div>
                    <div class="chart-value">${count}</div>
                </div>
            `;
        });
    }

    exportExcel() {
        if (typeof XLSX === 'undefined') {
            this.showNotification("La bibliothèque d'exportation n'est pas chargée.", "error");
            return;
        }

        if (this.filteredContacts.length === 0) {
            this.showNotification("Aucune donnée à exporter.", "warning");
            return;
        }

        const data = this.filteredContacts.map(c => ({
            'ID': c.id || '',
            'Prénom': c.first_name || '',
            'Nom': c.last_name || '',
            'Poste': c.position || '',
            'Entreprise': c.company || '',
            'Email': c.email || '',
            'Score (%)': c.score || 0,
            'Statut MX': c.mx_status || '',
            'Serveur MX': c.mx_server || '',
            'URL LinkedIn': c.linkedin_url || '',
            'Date': c.date || ''
        }));

        const ws = XLSX.utils.json_to_sheet(data);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Contacts");
        XLSX.writeFile(wb, `LinkedIn_Prospects_${new Date().toISOString().slice(0,10)}.xlsx`);
        this.showNotification("Export Excel téléchargé avec succès !", "success");
    }

    async copyEmails() {
        const validContacts = this.filteredContacts.filter(c => c.email && c.score >= 50);
        if (validContacts.length === 0) {
            this.showNotification("Aucun email valide trouvé.", "warning");
            return;
        }

        const emails = validContacts.map(c => c.email).join('\n');
        try {
            await navigator.clipboard.writeText(emails);
            this.showNotification(`${validContacts.length} emails copiés dans le presse-papier !`, "success");
        } catch (err) {
            this.showNotification("Erreur lors de la copie.", "error");
        }
    }

    downloadFile(content, filename, type) {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new LinkedInProspector();
});
