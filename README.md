# LinkedIn Prospector V3.2

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Outil de prospection professionnelle open source

## 🎯 Présentation
LinkedIn Prospector V3.2 est un outil open source complet permettant d'extraire des contacts professionnels qualifiés en utilisant une approche hybride (X-Ray + Stealth), de générer des adresses e-mail probables et de valider leur authenticité. Grâce à une combinaison de requêtes sur DuckDuckGo (X-Ray) et d'un navigateur headless furtif (Playwright Stealth), cet outil contourne les limitations traditionnelles tout en préservant un anonymat maximal.

## ✨ Fonctionnalités
- Scraping hybride (X-Ray DuckDuckGo + Playwright Stealth) pour un taux de réussite élevé.
- Génération d'emails intelligente avec 22 modèles (patterns) et 3 niveaux d'intensité.
- Validation des e-mails à plusieurs niveaux (syntaxe, enregistrements MX, SMTP optionnel et détection catch-all).
- Algorithme de scoring de confiance pour prioriser les e-mails les plus probables.
- Base de données locale (SQLite) avec sauvegarde continue et mode WAL pour éviter les pertes de données.
- Export professionnel au format Excel comprenant 11 colonnes.
- Interface Web de configuration statique (via GitHub Pages).
- Intégration GitHub Actions pour une exécution cloud automatisée et sans serveur.
- Mécanismes anti-détection multi-couches (rotation User-Agent, gestion des délais, etc.).
- Reprise après interruption (checkpoint) en cas d'échec ou d'arrêt volontaire.

## 📋 Prérequis
- Python 3.11 ou version supérieure
- Git

## 🚀 Installation

1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/username/linkedin-prospector.git
   cd linkedin-prospector
   ```

2. **Créer et activer un environnement virtuel** (recommandé) :
   ```bash
   python -m venv venv
   # Sous Windows
   venv\Scripts\activate
   # Sous Linux/Mac
   source venv/bin/activate
   ```

3. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

4. **Installer Playwright et les navigateurs** :
   ```bash
   playwright install chromium
   playwright install-deps
   ```

5. **Configurer les variables d'environnement** :
   Copiez le fichier d'exemple et complétez vos informations.
   ```bash
   cp .env.example .env
   ```

## ⚙️ Configuration
Le fichier `config/default.json` contient les paramètres principaux du comportement de l'outil.
Vous pouvez également définir des variables dans le fichier `.env` :
- `LI_AT_COOKIE` : Cookie de session LinkedIn (optionnel, pour l'approche furtive).
- `PROXY_URL` : URL d'un proxy pour masquer votre adresse IP.

Le fichier `company_domains.json` permet de faire correspondre manuellement le nom d'une entreprise à son nom de domaine pour la génération d'e-mails.

## 💻 Utilisation en Local
1. Lancez l'outil avec la configuration par défaut :
   ```bash
   python main.py --config config/default.json
   ```
2. Consultez les résultats dans le dossier `output/`.

## ☁️ Utilisation dans le Cloud (GitHub Actions)
1. Forkez ce dépôt.
2. Ajoutez vos secrets dans les paramètres de votre dépôt (Settings > Secrets and variables > Actions) : `LI_AT_COOKIE`, `PROXY_URL`.
3. Lancez manuellement le workflow `LinkedIn Prospector V3.2` ou attendez son exécution planifiée.
4. Téléchargez les artefacts contenant vos exports Excel et JSON à la fin du workflow.

## 🏗️ Architecture
L'architecture de l'application est conçue pour être modulaire et résiliente :
```
[Interface Web] --> [Config JSON]
                         |
[Main Runner] <----------+
   |--> [Scrapers (X-Ray / Stealth)]
   |--> [Email Generator]
   |--> [Email Validator]
   +--> [Database Manager]
```
Les flux de données sont orientés vers la base SQLite locale pour garantir la sécurité et la persistance avant export.

## 📊 Structure de la Base de Données
Le système utilise SQLite en mode WAL (Write-Ahead Logging) pour des performances d'écriture concurrentes optimales. 
Des index sont placés sur les champs `company`, `email` et `confidence_score` pour optimiser les requêtes.

## 📧 Génération d'Emails
Le système génère des e-mails en utilisant 3 niveaux :
- **Légère** (Light) : 4 patterns de base.
- **Moyenne** (Medium) : 11 patterns (incluant les prénoms composés).
- **Lourde** (Heavy) : 22 patterns exhaustifs couvrant pratiquement tous les formats d'entreprise.
Chaque e-mail reçoit un score basé sur les statistiques de réussite des entreprises.

## ✅ Validation des Emails
- **Syntaxe** : Vérification par expressions régulières.
- **MX** : Interrogation des serveurs DNS pour s'assurer que le domaine peut recevoir des e-mails.
- **SMTP** : (Optionnel) Connexion au serveur de messagerie pour vérifier l'existence de la boîte.
- **Catch-all** : Détection des serveurs qui acceptent tous les e-mails, réduisant la confiance dans la validation.

## 🔒 Sécurité & Anti-Détection
- **Warm-up** : Phase de chauffe pour simuler un comportement humain.
- **Rate limiting & Circuit breaker** : Pause automatique en cas de trop nombreuses requêtes bloquées.
- **Rotation User-Agent** : Changement régulier des en-têtes HTTP.

## 📁 Structure du Projet
- `main.py` : Point d'entrée du programme.
- `scrapers/` : Logique d'extraction des données.
- `enricher/` : Génération et validation d'e-mails.
- `storage/` : Gestion de la base de données.
- `tests/` : Tests unitaires.
- `config/` : Fichiers de configuration.

## 🧪 Tests
Exécutez les tests unitaires avec la commande :
```bash
pytest tests/ -v
```

## 📦 Export
L'export Excel généré comprend 11 colonnes, dont le prénom, nom, titre, entreprise, URL LinkedIn, e-mail estimé, score de confiance, et statut de validation. 

## ⚠️ Avertissements
- **Utilisation Éthique** : Cet outil doit être utilisé dans le respect du RGPD et des lois applicables concernant la prospection commerciale.
- **Conditions d'Utilisation** : L'utilisation de scrapers peut violer les Conditions de Service de certaines plateformes. Utilisez avec prudence.

## 📄 Licence
Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.
