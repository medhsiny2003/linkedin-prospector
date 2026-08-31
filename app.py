"""
Point d'entree racine universel avec Navigation Native Streamlit (st.navigation).
Assure le fonctionnement transparent de toutes les pages sur Cloud et Local.
"""

import os
import subprocess
import sys
from pathlib import Path
import streamlit as st

# Resolution des chemins universels
PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"

for p in [str(PROJECT_ROOT), str(APP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Installation automatique de Chromium pour Playwright en environnement Linux / Cloud
if sys.platform != "win32" and not os.path.exists("/tmp/.playwright_installed"):
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
        with open("/tmp/.playwright_installed", "w") as f:
            f.write("1")
    except Exception:
        pass

# Configuration globale de l'application
st.set_page_config(
    page_title="LinkedIn Prospector V3.1",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Chargement du style CSS
css_path = APP_DIR / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Definition officielle de la navigation native
nav_pages = [
    st.Page("pages/01_Dashboard.py", title="Tableau de Bord", icon="🏠", default=True),
    st.Page("pages/02_Configuration.py", title="Configuration", icon="⚙️"),
    st.Page("pages/03_Prospection.py", title="Prospection en Direct", icon="📊"),
    st.Page("pages/04_Contacts.py", title="Répertoire Contacts", icon="📋"),
    st.Page("pages/05_Export.py", title="Export Excel / CSV", icon="📤"),
    st.Page("pages/06_Logs.py", title="Journaux & Audit", icon="📜"),
]

pg = st.navigation(nav_pages)
pg.run()