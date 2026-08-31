---
title: LinkedIn Prospector V3.1
emoji: 🎯
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.37.0
app_file: app.py
pinned: false
license: mit
---

# 🚀 Assistant de Prospection LinkedIn (V3.1)
### *Automatisation éthique, sécurisée et ciblée pour la recherche de stage (Drones & Systèmes Embarqués en France)*
### *Interface Web Streamlit Professionnelle & Moteur Local Anti-Détection*

---

## ⚠️ AVERTISSEMENT CRITIQUE & COMPTE DÉDIÉ (À LIRE EN PRIORITÉ)

> [!WARNING]
> **En 2026, les algorithmes de détection de LinkedIn (Sentinelle / Bot-Detection) restreignent environ 40% des comptes appliquant des automatisations maladroites.**
> **NE JAMAIS UTILISER VOTRE COMPTE PERSONNEL PRINCIPAL POUR DE L'AUTOMATISATION DIRECTE.**

### 📋 Guide de Création d'un Compte Dédié :
1. **Identité / Email séparé** : Créez une nouvelle adresse email (ex: ProtonMail ou Gmail professionnel dédié).
2. **Numéro de téléphone distinct** : Utilisez une carte SIM prépayée ou un numéro virtuel dédié pour la validation 2FA SMS.
3. **Profil Réaliste & Cohérent** : Complétez le profil avec un intitulé professionnel lié au domaine (ex: *Assistant Recherche & Développement - Robotique / Systèmes Embarqués*), photo professionnelle, compétences et localisation en France.
4. **Phase d'échauffement (Warm-Up obligatoire)** : Suivez scrupuleusement le calendrier de warm-up sur 14 jours (géré automatiquement par l'outil).
5. **Mode Navigateur Visible** : Ne modifiez jamais `HEADLESS=false` dans le code ; LinkedIn détecte immédiatement les navigateurs sans rendu graphique (`headless`).

---

## 🌐 PROXIES RÉSIDENTIELS : RECOMMANDATIONS CTO

- **Pourquoi un Proxy Résidentiel ?** : Les adresses IP de Datacenter (AWS, OVH, DigitalOcean, Hetzner) sont indexées et immédiatement catégorisées comme suspectes par LinkedIn.
- **Bonne pratique** : Utilisez un proxy résidentiel rotatif ou statique localisé en France (ex: Bright Data, Smartproxy, IPRoyal).
- **Configuration** : Renseignez la variable `PROXY_URL=http://user:password@proxy_host:port` dans votre fichier `.env`. Si laissé vide, la connexion utilisera votre box Internet personnelle (connexion résidentielle naturelle).

---

## 💻 INTERFACE UTILISATEUR STREAMLIT (UI/UX V3.1)

Une interface web moderne et ergonomique respectant la charte graphique LinkedIn (#0A66C2) est fournie pour piloter l'outil en toute simplicité :

```
app/
├── streamlit_app.py              # Point d'entrée principal & routage
├── pages/
│   ├── 01_🏠_Dashboard.py        # 4 KPIs, 3 graphiques interactifs, 5 derniers contacts
│   ├── 02_⚙️_Configuration.py    # Formulaire de recherche, validateur li_at, profils sauvegardés
│   ├── 03_📊_Prospection.py      # Console temps réel, suivi de progression, arrêt d'urgence
│   ├── 04_📋_Contacts.py         # Répertoire interactif, recherche multi-critères, suppression
│   ├── 05_📤_Export.py           # Téléchargement Excel stylisé (.xlsx) & CSV
│   └── 06_📜_Logs.py             # Console d'audit, filtres de criticité, vérification SHA-256
├── components/                   # Composants réutilisables (sidebar, metrics, charts, notifications)
├── utils/                        # Traitement des données, gestion d'état, export en mémoire
└── styles/
    └── custom.css                # Feuille de style personnalisée LinkedIn
```

---

## ⚡ INSTALLATION RAPIDE

### 1. Prérequis
- **Python 3.12** installé sur votre machine.

### 2. Cloner / Se placer dans le répertoire
```bash
cd c:\Users\medhs\Downloads\autmation
```

### 3. Installer les dépendances Python
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configurer les variables d'environnement
Copiez `.env.example` en `.env` (si pas encore fait) et renseignez votre cookie `li_at` :
```env
LINKEDIN_COOKIE=AQED...votre_cookie_ici...
PROXY_URL=
DAILY_CONNECT_LIMIT=20
```

---

## 🖥️ LANCEMENT DE L'INTERFACE STREAMLIT

Pour ouvrir l'interface web dans votre navigateur :

```bash
streamlit run app/streamlit_app.py
```

### Options de lancement :
```bash
# Avec un port spécifique
streamlit run app/streamlit_app.py --server.port 8501

# Sans ouverture automatique du navigateur
streamlit run app/streamlit_app.py --server.headless true
```

---

## ⌨️ MODE LIGNE DE COMMANDE (CLI ALTERNATIVE)

Si vous préférez la console textuelle :
```bash
# Menu interactif en terminal
python main.py

# Exécution directe
python main.py --run --companies "Thales, Airbus, Safran" --titles "RH, Recruteur"

# Diagnostic santé & intégrité des logs
python main.py --check
python main.py --verify-audit
```

---

## 🧪 EXÉCUTION DES TESTS UNITAIRES

```bash
pytest -v
```

---

## 📧 DÉTAIL DES 11 PATTERNS D'EMAILS

| Priorité | Format | Exemple | Score de Confiance |
|---|---|---|:---:|
| **Haute** | `{first}.{last}@{domain}` | jean.dupont@thalesgroup.com | **95%** |
| **Haute** | `{first}{last}@{domain}` | jeandupont@thalesgroup.com | **90%** |
| **Haute** | `{f}.{last}@{domain}` | j.dupont@thalesgroup.com | **85%** |
| **Haute** | `{first}{l}@{domain}` | jeand@thalesgroup.com | **80%** |
| **Moyenne** | `{last}.{first}@{domain}` | dupont.jean@thalesgroup.com | **70%** |
| **Moyenne** | `{first}_{last}@{domain}` | jean_dupont@thalesgroup.com | **65%** |
| **Moyenne** | `{first}-{last}@{domain}` | jean-dupont@thalesgroup.com | **60%** |
| **Moyenne** | `{f}{last}@{domain}` | jdupont@thalesgroup.com | **55%** |
| **Basse** | `{first}@{domain}` | jean@thalesgroup.com | **40%** |
| **Basse** | `{last}@{domain}` | dupont@thalesgroup.com | **35%** |
| **Basse** | `{first}{last}1@{domain}` | jeandupont1@thalesgroup.com | **30%** |
