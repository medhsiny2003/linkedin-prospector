"""
Page 01 - Tableau de Bord Principal (Dashboard Pro).
Interface moderne avec dégradé LinkedIn, 4 KPIs, graphiques interactifs (2/1) et derniers contacts.
"""

import sys
from pathlib import Path
import pandas as pd
import streamlit as st

# Résolution des chemins
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
from core.worker.pipeline_worker import pipeline_worker
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
        page_title="Tableau de Bord | LinkedIn Prospector",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except Exception:
    pass

# Chargement du style CSS & Font Awesome
css_path = APP_DIR / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(
            f"""
            <head><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"></head>
            <style>{f.read()}</style>
            """,
            unsafe_allow_html=True
        )

init_session_state()
render_sidebar()

# 1. En-tête Stylisé avec Dégradé LinkedIn (#0A66C2 -> #004182)
st.markdown(
    """
    <div class="pro-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1><i class="fa-brands fa-linkedin" style="margin-right: 10px;"></i>Tableau de Bord de Prospection</h1>
                <p>Intelligence de détection des talents, vérification d'emails MX et qualification IA en temps réel.</p>
            </div>
            <div style="text-align: right;">
                <span class="badge-status badge-valide" style="font-size: 0.85rem; padding: 6px 14px;">
                    <i class="fa-solid fa-shield-halved"></i> Mode Sécurisé V3.1
                </span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# 2. Bannière de statut si prospection en cours
worker_status = pipeline_worker.get_status()
if worker_status["is_running"]:
    pct = worker_status["progress"]
    msg = worker_status["current_status"]
    session_leads_count = len(worker_status.get("recent_leads", []))
    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #EFF6FF 0%, #DBEAFE 100%); border-left: 5px solid #0A66C2; padding: 16px 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(10, 102, 194, 0.08);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong style="color: #0A66C2; font-size: 1.05rem;">
                    <i class="fa-solid fa-spinner fa-spin" style="margin-right: 8px;"></i>Prospection en direct ({int(pct * 100)}%)
                </strong>
                <span class="badge-status badge-valide">
                    <i class="fa-solid fa-user-check"></i> {session_leads_count} contact(s) qualifié(s)
                </span>
            </div>
            <div style="color: #334155; font-size: 0.9rem;">📍 <strong>Action en cours :</strong> {msg}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.progress(pct)

# 3. 4 Cartes Métriques KPIs en Ligne
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
    "status_label": f"⚡ {int(worker_status['progress'] * 100)}%" if worker_status["is_running"] else ("✅ Terminée" if recent_session_leads else "Prêt")
}

kpi_data = get_kpi_metrics()
render_kpi_cards(kpi_data, session_data=session_info)

# 4. Séparateur Visuel
st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

# 5. Colonnes Structurées (2/1) : Graphiques + Derniers Contacts
col_graph, col_contacts = st.columns([2, 1])

with col_graph:
    st.markdown(
        """
        <div class="pro-card-title">
            <i class="fa-solid fa-chart-pie" style="color: #0A66C2;"></i> Répartition & Distribution des Cibles
        </div>
        """,
        unsafe_allow_html=True
    )
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        df_status = get_status_distribution()
        render_status_donut_chart(df_status)
    with sub_col2:
        df_company = get_company_distribution(limit=6)
        render_company_bar_chart(df_company)

with col_contacts:
    st.markdown(
        """
        <div class="pro-card-title">
            <i class="fa-solid fa-clock-rotate-left" style="color: #8B5CF6;"></i> Derniers Contacts Qualifiés
        </div>
        """,
        unsafe_allow_html=True
    )
    
    recent_leads = get_recent_leads(limit=5)
    if not recent_leads.empty:
        for _, lead in recent_leads.iterrows():
            fname = str(lead.get("first_name", ""))
            lname = str(lead.get("last_name", ""))
            initials = f"{fname[:1]}{lname[:1]}".upper() or "IN"
            comp = str(lead.get("company", "Entreprise"))
            job = str(lead.get("job_title", "Poste"))
            email = str(lead.get("proposed_email", "Email non trouvé"))
            status = str(lead.get("status", "À vérifier"))
            
            # Badge de statut
            if "Validé" in status or str(lead.get("mx_verified", "")).lower() == "oui":
                badge_class = "badge-valide"
                badge_icon = "fa-check-circle"
                badge_label = "Validé MX"
            elif "Catch-All" in status or "vérifier" in status:
                badge_class = "badge-a-verifier"
                badge_icon = "fa-triangle-exclamation"
                badge_label = "À vérifier"
            else:
                badge_class = "badge-invalide"
                badge_icon = "fa-circle-xmark"
                badge_label = "Invalide"

            contact_html = f"""
            <div class="contact-item">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div class="contact-avatar">{initials}</div>
                    <div>
                        <div style="font-weight: 700; color: #0F172A; font-size: 0.9rem;">{fname} {lname}</div>
                        <div style="font-size: 0.78rem; color: #64748B;">{job[:24]}{'...' if len(job) > 24 else ''} • <strong>{comp}</strong></div>
                        <div style="font-size: 0.75rem; color: #0A66C2; font-family: monospace;">{email}</div>
                    </div>
                </div>
                <div>
                    <span class="badge-status {badge_class}">
                        <i class="fa-solid {badge_icon}"></i> {badge_label}
                    </span>
                </div>
            </div>
            """
            st.markdown(contact_html, unsafe_allow_html=True)
    else:
        st.info("Aucun contact qualifié pour l'instant.")

# 6. Séparateur & Actions Rapides
st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="pro-card-title">
        <i class="fa-solid fa-bolt" style="color: #F59E0B;"></i> Actions Rapides & Navigation
    </div>
    """,
    unsafe_allow_html=True
)

act1, act2, act3 = st.columns(3)
with act1:
    if st.button("🚀 Lancer une Prospection", type="primary", use_container_width=True):
        st.switch_page("pages/03_Prospection.py")
with act2:
    if st.button("👥 Consulter la Base de Contacts", use_container_width=True):
        st.switch_page("pages/04_Contacts.py")
with act3:
    if st.button("📥 Télécharger l'Export Excel", use_container_width=True):
        st.switch_page("pages/05_Export.py")