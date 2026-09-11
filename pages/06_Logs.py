"""
Page 06 - Journal d'Audit Cryptographique (Tamper-Evident SHA-256).
Visualisation des traces, filtres de criticité et vérification d'intégrité de la chaîne.
"""

import json
from pathlib import Path
import sys
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = Path(__file__).resolve().parent.parent
for p in [str(PROJECT_ROOT), str(APP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from components.sidebar import render_sidebar
from config import config
from core.monitoring.audit_logger import audit_logger
from utils.state_manager import init_session_state

try:
    st.set_page_config(
    page_title="Logs & Audit | LinkedIn Prospector V3.1",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)
except Exception:
    pass

from components.ui_loader import apply_custom_css
apply_custom_css(APP_DIR)

init_session_state()
render_sidebar()

st.title("📜 Journal d'Audit & Sécurité")
st.markdown("Traçabilité cryptographique de chaque requête, décision anti-détection et événement.")

# 1. Vérification d'intégrité en un clic
col_v1, col_v2, _ = st.columns([3, 3, 4])

with col_v1:
    if st.button("🛡️ Vérifier l'intégrité SHA-256", use_container_width=True, type="primary"):
        is_valid = audit_logger.verify_integrity()
        if is_valid:
            st.success("✅ Intégrité validée : Aucun bloc n'a été altéré.", icon="🔒")
        else:
            st.error("❌ Rupture de chaîne détectée dans audit.json !", icon="🚨")

with col_v2:
    if config.AUDIT_LOG_PATH.exists():
        with open(config.AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            raw_json = f.read()
        st.download_button(
            label="📥 Télécharger audit.json",
            data=raw_json,
            file_name="audit.json",
            mime="application/json",
            use_container_width=True
        )

st.markdown("<hr style='margin: 16px 0; border-color: #E0E4E8;'/>", unsafe_allow_html=True)

# 2. Lecture des logs
logs_chain = []
if config.AUDIT_LOG_PATH.exists():
    try:
        with open(config.AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            logs_chain = json.load(f)
    except Exception as e:
        st.error(f"Erreur de lecture du fichier audit.json : {e}")

if not logs_chain:
    st.info("Le journal d'audit est actuellement vide.")
else:
    f_col1, f_col2 = st.columns([3, 4])
    with f_col1:
        event_types = sorted(list(set(e.get("event_type", "UNKNOWN") for e in logs_chain)))
        selected_types = st.multiselect("Filtrer par type d'événement :", event_types, default=[])
    with f_col2:
        search_log = st.text_input("Recherche dans les messages de logs :", placeholder="Ex: WARMUP, EXCEL, HTTP...")

    filtered_logs = logs_chain
    if selected_types:
        filtered_logs = [e for e in filtered_logs if e.get("event_type") in selected_types]
    if search_log.strip():
        q = search_log.strip().lower()
        filtered_logs = [e for e in filtered_logs if q in e.get("message", "").lower() or q in e.get("event_type", "").lower()]

    st.caption(f"Affichage de **{len(filtered_logs)}** événement(s) sur un total de **{len(logs_chain)}** blocs chaînés.")

    log_html = "<div class='log-console'>"
    for item in reversed(filtered_logs):
        etype = item.get("event_type", "")
        ts = item.get("timestamp", "").split("T")[1][:8] if "T" in item.get("timestamp", "") else item.get("timestamp", "")
        msg = item.get("message", "")
        h = item.get("hash", "")[:8]

        css_class = "log-info"
        if "RISK" in etype or "ERROR" in etype or "FAIL" in etype:
            css_class = "log-error"
        elif "WARN" in etype or "PAUSE" in etype or "BLOCKED" in etype:
            css_class = "log-warn"
        elif "SUCCESS" in etype or "VALID" in etype:
            css_class = "log-success"

        log_html += f"<div class='log-entry'><span style='color: #8B949E;'>[{ts}]</span> <span class='{css_class}'>[{etype}]</span> {msg} <span style='color: #484F58; font-size: 0.75rem;'>({h}...)</span></div>"

    log_html += "</div>"
    st.markdown(log_html, unsafe_allow_html=True)
