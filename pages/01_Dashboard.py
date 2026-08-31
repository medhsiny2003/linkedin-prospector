"""
Page 01 - Tableau de Bord Principal (Dashboard).
Visualisation des métriques clés (KPIs), graphiques d'analyse et derniers contacts.
"""

import sys
import streamlit as st
from pathlib import Path

# Resolution universelle et robuste des chemins
current_file = Path(__file__).resolve()
PROJECT_ROOT = None
for parent in [current_file.parent, current_file.parent.parent, current_file.parent.parent.parent]:
    if (parent / "config.py").exists():
        PROJECT_ROOT = parent
        break
if not PROJECT_ROOT:
    PROJECT_ROOT = current_file.parent.parent

APP_DIR = PROJECT_ROOT / "app"
for p in [str(PROJECT_ROOT), str(APP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from components.charts import (
    render_company_bar_chart,
    render_status_donut_chart,
    render_timeline_chart
)
from components.metrics import render_kpi_cards
from components.notifications import show_security_banner
from components.sidebar import render_sidebar
from utils.data_processor import (
    get_company_distribution,
    get_kpi_metrics,
    get_recent_leads,
    get_status_distribution,
    get_timeline_distribution
)
from utils.state_manager import init_session_state

try:
    st.set_page_config(
    page_title="Dashboard | LinkedIn Prospector V3.1",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)
except Exception:
    pass

# Chargement du style CSS
css_path = APP_DIR / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session_state()
render_sidebar()

from core.worker.pipeline_worker import pipeline_worker

# En-tête
st.markdown(
    """
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div>
            <h1 style="margin-bottom: 0;">🏠 Tableau de Bord</h1>
            <p style="color: #666666; font-size: 1rem; margin-top: 4px;">
                Vue synthétique de votre prospection de stage en France (Drones & Systèmes Embarqués).
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

worker_status = pipeline_worker.get_status()
if worker_status["is_running"]:
    pct = worker_status["progress"]
    msg = worker_status["current_status"]
    session_leads_count = len(worker_status.get("recent_leads", []))
    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #E8F0FE 0%, #D2E3FC 100%); border-left: 5px solid #1967D2; padding: 14px 18px; border-radius: 8px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <strong style="color: #1967D2; font-size: 1rem;">⚡ Prospection en cours en direct ({int(pct * 100)}%)</strong>
                <span style="background: #1967D2; color: #FFFFFF; padding: 2px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: bold;">
                    👤 {session_leads_count} contact(s) qualifié(s) dans cette session
                </span>
            </div>
            <div style="color: #333333; font-size: 0.9rem;">📍 <strong>Action active :</strong> {msg}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.progress(pct)

show_security_banner()

# 1. KPIs de Session & Globaux (Réinitialisés à chaque session)
recent_session_leads = worker_status.get("recent_leads", [])
session_valid_count = len([
    l for l in recent_session_leads 
    if "Validé" in str(l.get("status", "")) or str(l.get("mx_verified", "")).lower() == "oui"
])
session_companies_count = len(set(l.get("company", "") for l in recent_session_leads if l.get("company")))

session_info = {
    "is_running": worker_status["is_running"],
    "session_count": len(recent_session_leads),
    "session_valid": session_valid_count,
    "session_companies": session_companies_count,
    "status_label": f"⚡ En cours ({int(worker_status['progress'] * 100)}%)" if worker_status["is_running"] else ("✅ Terminée" if recent_session_leads else "Prêt")
}

kpi_data = get_kpi_metrics()
render_kpi_cards(kpi_data, session_data=session_info)

st.markdown("<br/>", unsafe_allow_html=True)

# 2. Graphiques
col_left, col_right = st.columns([6, 4])

with col_left:
    df_company = get_company_distribution(limit=8)
    render_company_bar_chart(df_company)

with col_right:
    df_status = get_status_distribution()
    render_status_donut_chart(df_status)

# Graphique chronologique
df_timeline = get_timeline_distribution()
if not df_timeline.empty and len(df_timeline) > 1:
    st.markdown("<br/>", unsafe_allow_html=True)
    render_timeline_chart(df_timeline)

st.markdown("<br/>", unsafe_allow_html=True)

# 3. Tableau des Contacts en Temps Réel (Strictement IDENTIQUE à la page Prospection)
import pandas as pd
if recent_session_leads:
    st.markdown(f"### 👤 Contacts Trouvés en Temps Réel dans cette Session ({len(recent_session_leads)})")
    cols_live = ["first_name", "last_name", "job_title", "company", "proposed_email", "confidence_score", "status"]
    df_live = pd.DataFrame(recent_session_leads)
    df_live_display = df_live[[c for c in cols_live if c in df_live.columns]]
    st.dataframe(
        df_live_display.tail(10),
        column_config={
            "first_name": "Prénom",
            "last_name": "Nom",
            "job_title": "Poste",
            "company": "Entreprise",
            "proposed_email": "Email Proposé",
            "confidence_score": st.column_config.ProgressColumn(
                "Score",
                format="%d%%",
                min_value=0,
                max_value=100
            ),
            "status": "Statut MX"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.markdown("### 📋 10 Derniers Contacts Enregistrés dans la Base SQLite")
    df_recent = get_recent_leads(limit=10)
    if not df_recent.empty:
        cols_live = ["first_name", "last_name", "job_title", "company", "proposed_email", "confidence_score", "status"]
        df_display = df_recent[[c for c in cols_live if c in df_recent.columns]]
        st.dataframe(
            df_display,
            column_config={
                "first_name": "Prénom",
                "last_name": "Nom",
                "job_title": "Poste",
                "company": "Entreprise",
                "proposed_email": "Email Proposé",
                "confidence_score": st.column_config.ProgressColumn(
                    "Score",
                    format="%d%%",
                    min_value=0,
                    max_value=100
                ),
                "status": "Statut MX"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Aucun contact enregistré pour l'instant. Lancez votre première recherche depuis l'onglet Prospection !")

# 4. Actions Rapides
st.markdown("<br/>", unsafe_allow_html=True)
st.markdown("### ⚡ Actions Rapides")
act_col1, act_col2, _ = st.columns([3, 3, 6])

with act_col1:
    if st.button("🚀 Lancer une Prospection", use_container_width=True, type="primary"):
        st.switch_page("pages/03_Prospection.py")

with act_col2:
    if st.button("📤 Exporter les Contacts", use_container_width=True):
        st.switch_page("pages/05_Export.py")

with _:
    if st.button("🔄 Actualiser les Données", use_container_width=False):
        st.rerun()

# Rafraîchissement automatique du Dashboard si une prospection est en cours
if worker_status["is_running"]:
    import time
    time.sleep(2.0)
    st.rerun()
