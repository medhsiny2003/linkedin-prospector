"""
Point d'entree racine universel pour Streamlit Community Cloud, Hugging Face Spaces et local.
Initialise automatiquement les chemins, le style et redirige vers le Dashboard.
"""

import os
import subprocess
import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"

for p in [str(PROJECT_ROOT), str(APP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Installation automatique et silencieuse de Chromium pour Playwright en environnement Linux / Cloud
if sys.platform != "win32" and not os.path.exists("/tmp/.playwright_installed"):
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
        with open("/tmp/.playwright_installed", "w") as f:
            f.write("1")
    except Exception:
        pass

from app.components.sidebar import render_sidebar
from app.utils.state_manager import init_session_state

st.set_page_config(
    page_title="LinkedIn Prospector V3.1",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Chargement du style CSS personnalise
css_path = APP_DIR / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session_state()
render_sidebar()

# Redirection automatique vers la page Dashboard
st.switch_page("pages/01_Dashboard.py")