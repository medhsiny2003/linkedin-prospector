"""
Point d'entrée principal pour l'application Streamlit.
Redirige ou affiche directement la page d'accueil (Dashboard).
"""

import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent
for p in [str(PROJECT_ROOT), str(APP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from components.sidebar import render_sidebar
from utils.state_manager import init_session_state

st.set_page_config(
    page_title="LinkedIn Prospector V3.1",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Chargement du style CSS personnalisé
css_path = APP_DIR / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session_state()
render_sidebar()

# Redirection automatique vers la page Dashboard
st.switch_page("pages/01_Dashboard.py")
