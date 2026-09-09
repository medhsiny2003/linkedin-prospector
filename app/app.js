/**
 * LinkedIn Prospector V3.2 — Client-Side Logic & Supervision Table
 * 100% Static GitHub Pages Compatible
 */

class ProspectorApp {
    constructor() {
        this.prospects = [];
        this.filtered = [];
        this.currentPage = 1;
        this.pageSize = 25;
        this.sortCol = 'confidence_score';
        this.sortAsc = false;

        this.init();
    }

    init() {
        // Form & Config Download
        const btnGen = document.getElementById('btn-generate-config');
        if (btnGen) btnGen.addEventListener('click', () => this.generateConfig());

        // File Upload
        const btnOpenFile = document.getElementById('btn-open-file');
        const fileInput = document.getElementById('file-input');
        if (btnOpenFile && fileInput) {
            btnOpenFile.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        }

        // Search Filter
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.filterData(e.target.value));
        }

        // Export Actions
        const btnExcel = document.getElementById('btn-export-excel');
        if (btnExcel) btnExcel.addEventListener('click', () => this.exportExcelDeduplicated());

        const btnCopy = document.getElementById('btn-copy-emails');
        if (btnCopy) btnCopy.addEventListener('click', () => this.copyValidEmails());

        // Table Sorting
        document.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', () => this.sortBy(th.dataset.sort));
        });

        // Pagination
        const btnPrev = document.getElementById('btn-prev');
        const btnNext = document.getElementById('btn-next');
        if (btnPrev) btnPrev.addEventListener('click', () => { if (this.currentPage > 1) { this.currentPage--; this.renderTable(); } });
        if (btnNext) btnNext.addEventListener('click', () => { if (this.currentPage < this.totalPages) { this.currentPage++; this.renderTable(); } });

        // Auto-fetch if local server is running
        this.tryFetchLocalData();
    }

    async tryFetchLocalData() {
        try {
            const res = await fetch('/api/results');
            if (res.ok) {
                const data = await res.json();
                if (data && data.contacts && data.contacts.length > 0) {
                    this.loadData(data.contacts);
                }
            }
        } catch (e) {
            // Static mode (GitHub Pages), ignore
        }
    }

    generateConfig() {
        const companies = document.getElementById('companies').value.split('\n').map(s => s.trim()).filter(s => s);
        const keywords = document.getElementById('keywords').value.split('\n').map(s => s.trim()).filter(s => s);
        const location = document.getElementById('location').value.trim() || "France";
        const email_level = document.getElementById('email_level').value;

        if (companies.length === 0 || keywords.length === 0) {
            this.showToast("Veuillez renseigner au moins une entreprise et un poste.", "warning");
            return;
        }

        const config = {
            companies,
            keywords,
            location,
            email_level,
            max_results_per_company: 50,
            rate_limit_rpm: 20
        };

        const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'config.json';
        a.click();
        this.showToast("Fichier config.json téléchargé !", "success");
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const parsed = JSON.parse(e.target.result);
                const items = Array.isArray(parsed) ? parsed : (parsed.contacts || []);
                this.loadData(items);
                this.showToast(`${this.prospects.length} profils uniques chargés avec succès.`, "success");
            } catch (err) {
                this.showToast("Erreur lors de la lecture du fichier JSON.", "error");
            }
        };
        reader.readAsText(file);
    }

    deduplicate(items) {
        const map = new Map();
        items.forEach(p => {
            const fn = (p.first_name || '').trim();
            const ln = (p.last_name || '').trim();
            const comp = (p.company || '').trim();
            const score = parseInt(p.confidence_score || p.score || 0, 10);

            const key = `${fn.toLowerCase()}|${ln.toLowerCase()}|${comp.toLowerCase()}`;
            if (!map.has(key) || score > (map.get(key).confidence_score || 0)) {
                map.set(key, {
                    first_name: fn,
                    last_name: ln,
                    title: p.title || p.position || '',
                    company: comp,
                    email: p.email || '',
                    email_alt1: p.email_alt1 || '',
                    confidence_score: score,
                    mx_status: p.mx_status || 'unknown',
                    linkedin_url: p.linkedin_url || ''
                });
            }
        });
        return Array.from(map.values());
    }

    loadData(items) {
        this.prospects = this.deduplicate(items);
        this.filtered = [...this.prospects];
        this.currentPage = 1;
        this.updateKPIs();
        this.renderTable();
    }

    updateKPIs() {
        const total = this.prospects.length;
        const valid = this.prospects.filter(p => (p.mx_status || '').toLowerCase() === 'valid').length;
        const verify = this.prospects.filter(p => {
            const s = (p.mx_status || '').toLowerCase();
            return s.includes('catch') || s === 'unknown';
        }).length;
        const scores = this.prospects.map(p => p.confidence_score).filter(s => s > 0);
        const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;

        document.getElementById('kpi-total').textContent = total;
        document.getElementById('kpi-valid').textContent = valid;
        document.getElementById('kpi-verify').textContent = verify;
        document.getElementById('kpi-score').textContent = `${avgScore}%`;
    }

    filterData(query) {
        const q = (query || '').toLowerCase().trim();
        if (!q) {
            this.filtered = [...this.prospects];
        } else {
            this.filtered = this.prospects.filter(p =>
                (p.first_name || '').toLowerCase().includes(q) ||
                (p.last_name || '').toLowerCase().includes(q) ||
                (p.title || '').toLowerCase().includes(q) ||
                (p.company || '').toLowerCase().includes(q) ||
                (p.email || '').toLowerCase().includes(q)
            );
        }
        this.currentPage = 1;
        this.renderTable();
    }

    sortBy(col) {
        if (this.sortCol === col) {
            this.sortAsc = !this.sortAsc;
        } else {
            this.sortCol = col;
            this.sortAsc = true;
        }

        this.filtered.sort((a, b) => {
            let vA = a[col] ?? '';
            let vB = b[col] ?? '';

            if (typeof vA === 'string') vA = vA.toLowerCase();
            if (typeof vB === 'string') vB = vB.toLowerCase();

            if (vA < vB) return this.sortAsc ? -1 : 1;
            if (vA > vB) return this.sortAsc ? 1 : -1;
            return 0;
        });

        this.renderTable();
    }

    get totalPages() {
        return Math.ceil(this.filtered.length / this.pageSize) || 1;
    }

    renderTable() {
        const tbody = document.getElementById('table-body');
        if (!tbody) return;

        if (this.filtered.length === 0) {
            tbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="8">Aucun résultat trouvé pour votre recherche.</td>
                </tr>
            `;
            document.getElementById('page-info').textContent = "Page 1 / 1";
            document.getElementById('btn-prev').disabled = true;
            document.getElementById('btn-next').disabled = true;
            return;
        }

        const start = (this.currentPage - 1) * this.pageSize;
        const pageItems = this.filtered.slice(start, start + this.pageSize);

        tbody.innerHTML = pageItems.map(p => {
            // Status badge
            let statusBadge = '';
            const status = (p.mx_status || '').toLowerCase();
            if (status === 'valid') {
                statusBadge = '<span class="badge badge-success">Validé</span>';
            } else if (status.includes('catch') || status === 'unknown' || p.confidence_score >= 50) {
                statusBadge = '<span class="badge badge-warning">À vérifier</span>';
            } else {
                statusBadge = '<span class="badge badge-danger">Invalide</span>';
            }

            // LinkedIn verification URL
            let linkedinUrl = p.linkedin_url;
            if (!linkedinUrl || !linkedinUrl.includes('linkedin.com/in/')) {
                const searchQ = encodeURIComponent(`${p.first_name} ${p.last_name} ${p.company}`);
                linkedinUrl = `https://www.linkedin.com/search/results/all/?keywords=${searchQ}`;
            }

            return `
                <tr>
                    <td><strong>${p.first_name || '-'}</strong></td>
                    <td><strong>${p.last_name || '-'}</strong></td>
                    <td>${p.title || '-'}</td>
                    <td>${p.company || '-'}</td>
                    <td><code>${p.email || '-'}</code></td>
                    <td><strong>${p.confidence_score || 0}%</strong></td>
                    <td>${statusBadge}</td>
                    <td>
                        <a href="${linkedinUrl}" target="_blank" rel="noopener" class="linkedin-link">
                            🔍 Vérifier sur LinkedIn
                        </a>
                    </td>
                </tr>
            `;
        }).join('');

        document.getElementById('page-info').textContent = `Page ${this.currentPage} / ${this.totalPages}`;
        document.getElementById('btn-prev').disabled = (this.currentPage === 1);
        document.getElementById('btn-next').disabled = (this.currentPage === this.totalPages);
    }

    exportExcelDeduplicated() {
        if (typeof XLSX === 'undefined') {
            this.showToast("Bibliothèque XLSX non chargée.", "error");
            return;
        }

        if (this.prospects.length === 0) {
            this.showToast("Aucune donnée à exporter.", "warning");
            return;
        }

        const rows = this.prospects.map((p, idx) => ({
            "ID": idx + 1,
            "Prénom": p.first_name,
            "Nom": p.last_name,
            "Poste": p.title,
            "Entreprise": p.company,
            "Email Principal": p.email,
            "Score Confiance (%)": p.confidence_score,
            "Statut": (p.mx_status || '').toLowerCase() === 'valid' ? 'Validé' : 'À vérifier',
            "Email Alternatif": p.email_alt1 || '',
            "URL LinkedIn": p.linkedin_url || ''
        }));

        const ws = XLSX.utils.json_to_sheet(rows);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Prospects LinkedIn");

        const dateStr = new Date().toISOString().slice(0, 10);
        XLSX.writeFile(wb, `LinkedIn_Prospects_${dateStr}_Dédoublonné.xlsx`);
        this.showToast(`Export Excel réussi : ${rows.length} contacts uniques !`, "success");
    }

    async copyValidEmails() {
        const valid = this.prospects.filter(p => p.email && p.confidence_score >= 50);
        if (valid.length === 0) {
            this.showToast("Aucun email valide à copier.", "warning");
            return;
        }

        const text = valid.map(p => p.email).join('\n');
        try {
            await navigator.clipboard.writeText(text);
            this.showToast(`${valid.length} emails copiés dans le presse-papier !`, "success");
        } catch (e) {
            this.showToast("Erreur lors de la copie.", "error");
        }
    }

    showToast(msg, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const el = document.createElement('div');
        el.className = `toast ${type}`;
        el.textContent = msg;
        container.appendChild(el);

        setTimeout(() => {
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 300);
        }, 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ProspectorApp();
});
