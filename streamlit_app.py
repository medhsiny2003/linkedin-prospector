"""
==============================================================================
 LinkedIn Prospector V3.1 - Application Principale Streamlit
 Point d'entrée Universel avec Navigation Native, Design Pro LinkedIn & 24/7 Cloud
==============================================================================
"""

import os
import sys
from pathlib import Path
import streamlit as st

# 1. Résolution universelle des chemins
PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"

for p in [str(PROJECT_ROOT), str(APP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# 2. Configuration Globale de la Page
try:
    st.set_page_config(
        page_title="LinkedIn Prospector V3.1",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except Exception:
    pass

# 3. Injection Font Awesome 6 & Feuille de Styles Pro
from components.ui_loader import apply_custom_css
apply_custom_css(APP_DIR)

# 4. Installation silencieuse automatique de Chromium si nécessaire sur Cloud
if sys.platform != "win32" and not os.path.exists("/tmp/.chromium_ready"):
    try:
        import subprocess
        subprocess.run(["playwright", "install", "chromium"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open("/tmp/.chromium_ready", "w") as f:
            f.write("ready")
    except Exception:
        pass

# 5. Déclaration des Pages Multi-Pages avec Navigation Native
pages = [
    st.Page("pages/01_Dashboard.py", title="Tableau de Bord", icon="🏠", default=True),
    st.Page("pages/02_Configuration.py", title="Configuration", icon="⚙️"),
    st.Page("pages/03_Prospection.py", title="Prospection en Direct", icon="📊"),
    st.Page("pages/04_Contacts.py", title="Base de Contacts", icon="👥"),
    st.Page("pages/05_Export.py", title="Exportation Excel", icon="📥"),
    st.Page("pages/06_Logs.py", title="Journal d'Audit", icon="📜"),
]

nav = st.navigation(pages)
nav.run()