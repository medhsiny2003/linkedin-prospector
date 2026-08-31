# 📘 Dossier Technique & Architecture Système - LinkedIn Prospector V3.1

> **Document de Référence Technique & Décisionnel (Niveau CTO / Lead Architect)**  
> **Auteur :** Antigravity Engineering & Architecture Team  
> **Version du Système :** V3.1 Stable  

---

## 🎯 1. Les 3 Modes & Environnements d'Exécution

Le système est rigoureusement structuré autour de **3 modes d'exécution étanches** adaptés aux spécificités de chaque environnement :

| Mode | Environnement | Moteur d'Exécution | Gestion de Session & Cookies | Rôle & Fonctionnalité |
| :--- | :--- | :--- | :--- | :--- |
| **💻 Mode Local** | Windows 10/11 | Playwright Microsoft Edge | Profil persistant (`user-data-dir`) & Cookies | Scraping visuel haute fidélité en direct sur votre écran de PC. |
| **☁️ Mode Cloud** | GitHub Actions (Linux Ubuntu) | Chromium Headless + X-Ray OSINT | Zéro session (Mode public déchiffré) | Prospection automatisée programmée (cron / déclenchement manuel). |
| **📱 Mode Visualiseur (UI)** | Streamlit Cloud (Snowflake) | Python / Pandas / SQLite | Lecture seule de `leads.db` & Excel | Tableau de bord de consultation, graphiques et téléchargement des exports. |

---

## 🏛️ 2. Architecture Système & Flux de Données

```mermaid
flowchart TB
    subgraph UI_LAYER["📱 Streamlit Cloud (Visualiseur Lecture Seule)"]
        DASH["01_Dashboard (KPIs & Visualisations Plotly)"]
        CONF["02_Configuration (Gestion des Profils Cibles)"]
        PROS["03_Prospection (Déclencheur & Supervision)"]
        CONT["04_Contacts (Grille Filtrable des Leads)"]
        EXPO["05_Export (Téléchargement Session & Historique)"]
    end

    subgraph ENGINE_LOCAL["💻 Mode Local (Windows)"]
        EDGE["Microsoft Edge (Profil Persistant)"]
        LOCAL_SCRAPER["Scraping LinkedIn Direct"]
    end

    subgraph ENGINE_CLOUD["☁️ Mode Cloud (GitHub Actions Linux Ubuntu)"]
        CRON["Déclencheur Programmé (Cron / Manuel)"]
        CHROMIUM_HEADLESS["Chromium Linux Headless"]
        XRAY_OSINT["Moteur X-Ray OSINT (Google & Bing Décodé)"]
    end

    subgraph ENRICH_CORE["🧠 Moteur d'Enrichissement & Validation"]
        SEMANTIC_AI["Filtre Sémantique & IA (Gemini / Métiers)"]
        EMAIL_ORCH["Orchestrateur d'Emails 5 Couches"]
        DNS_VALIDATOR["Vérificateur DNS / MX Asynchrone"]
    end

    subgraph DATA_STORAGE["💾 Stockage Persistant & Rotation"]
        SQLITE[("SQLite (leads.db - Mode WAL)")]
        EXCEL_SESSION["contacts_stage.xlsx (Session Active)"]
        EXCEL_HIST["contacts_historique.xlsx (Base Cumulée)"]
        GIT_REPO["Dépôt Git Privé (Synchronisation)"]
    end

    PROS -->|Bouton Mode Local| ENGINE_LOCAL
    PROS -->|Bouton Mode Cloud| CRON
    CRON --> CHROMIUM_HEADLESS --> XRAY_OSINT

    ENGINE_LOCAL --> ENRICH_CORE
    XRAY_OSINT --> ENRICH_CORE

    ENRICH_CORE --> DATA_STORAGE
    DATA_STORAGE -->|Mise à jour Git [skip ci]| GIT_REPO
    GIT_REPO -->|Lecture Directe| UI_LAYER
```

---

## 🔄 3. Système de Rotation des Fichiers Excel (Session vs Historique)

Pour éviter toute confusion et garantir la conservation intégrale des données historiques :

1. **`contacts_stage.xlsx` (Fichier de Session Active) :**
   * Contient **uniquement les contacts qualifiés lors de la session en cours**.
   * Réinitialisé au début de chaque nouvelle recherche.
2. **`contacts_historique.xlsx` (Archive Globale Cumulée) :**
   * Fusionne et conserve la totalité de vos contacts extraits au fil des sessions.
   * Contient déjà vos **209 contacts qualifiés** et s'enrichit automatiquement sans jamais rien écraser.

---

## 🛡️ 4. Matrice de Fiabilité & Résolution des Contraintes Techniques

| Contrainte Technique | Solution Implémentée | Garantie CTO |
| :--- | :--- | :---: |
| **Absence d'Edge sur Linux (Cloud)** | Utilisation exclusive de Chromium officiel avec installation des dépendances Linux (`playwright install --with-deps chromium`). | ✅ 100% Compatible Linux |
| **Blocage IP Datacenter Cloud** | Basculement immédiat vers le Moteur X-Ray OSINT public sans obligation de session. | ✅ Zéro Erreur Redirection |
| **URLs de redirection Bing chiffrées** | Décodeur Base64 automatique (`decode_search_url`) pour restituer les vraies URLs `ma.linkedin.com/in/...`. | ✅ Déduplication Fiable |
| **Persistance des données sans perte** | Écriture immédiate contact par contact dans SQLite (WAL) et commit Git automatique après chaque exécution. | ✅ Zéro Perte de Données |