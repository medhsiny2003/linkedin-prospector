"""
Page 03 - Centre de Prospection en Direct (Architecture Découplée & Résiliente).
Exécute le scraping dans un thread d'arrière-plan dédié :
- La navigation entre les pages (Dashboard, Contacts, Export) ne ferme plus Microsoft Edge !
- Affichage de la progression dynamique, console en direct et contacts trouvés en temps réel.
"""

import time
from datetime import datetime
from pathlib import Path
import sys
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = Path(__file__).resolve().parent.parent
for p in [str(PROJECT_ROOT), str(APP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from components.notifications import show_security_banner, show_toast
from components.sidebar import render_sidebar
from core.worker.pipeline_worker import pipeline_worker
from utils.data_processor import get_recent_leads
from utils.state_manager import init_session_state

st.set_page_config(
    page_title="Prospection | LinkedIn Prospector V3.1",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Chargement du style CSS
css_path = APP_DIR / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

from app.utils.state_manager import init_session_state, get_active_config, save_active_config, get_saved_profiles

init_session_state()
render_sidebar()

st.title("📊 Centre de Prospection en Direct")
st.markdown("Prospection multi-entreprises automatisée sur **Microsoft Edge** avec exécution résiliente en arrière-plan.")

show_security_banner()

# Synchronisation directe depuis la Configuration
active_cfg = get_active_config()
saved_profiles = get_saved_profiles()
saved_names = list(saved_profiles.keys())

# Récupération des valeurs configurées
current_profile = st.session_state.get("selected_profile", active_cfg.get("selected_profile", saved_names[0] if saved_names else "Profil Personnalisé"))
companies_str = st.session_state.get("companies", active_cfg.get("companies", ""))
titles_str = st.session_state.get("job_titles", active_cfg.get("job_titles", ""))
location_val = st.session_state.get("location", active_cfg.get("location", "Maroc"))
max_contacts_val = st.session_state.get("max_contacts", active_cfg.get("max_contacts", 20))

companies_list = [c.strip() for c in companies_str.split(",") if c.strip()]
titles_list = [t.strip() for t in titles_str.split(",") if t.strip()]

summary_card = f"""
<div style="background: #FFFFFF; border: 1px solid #E0E4E8; border-radius: 10px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <h4 style="margin: 0; color: #0A66C2;">🎯 Configuration Active : <span style="color: #057642;">{current_profile}</span></h4>
    </div>
    <div style="font-size: 0.9rem; color: #333333; line-height: 1.6;">
        <strong>Entreprises ({len(companies_list)}) :</strong> {', '.join(companies_list[:8])}{'...' if len(companies_list) > 8 else ''}<br/>
        <strong>Postes ciblés ({len(titles_list)}) :</strong> {', '.join(titles_list[:4])}{'...' if len(titles_list) > 4 else ''}<br/>
        <strong>Localisation :</strong> <span style="background: #E8F0FE; color: #1967D2; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{location_val}</span> &nbsp;|&nbsp; <strong>Limite par cible :</strong> {max_contacts_val} profils
    </div>
</div>
"""
st.markdown(summary_card, unsafe_allow_html=True)

# Récupération de l'état du worker
worker_status = pipeline_worker.get_status()
is_job_running = worker_status["is_running"]
is_job_paused = worker_status.get("is_paused", False)

# Barre de Contrôles Complète
col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([3, 2, 2, 3])

with col_btn1:
    start_clicked = st.button(
        "🚀 Lancer la Prospection",
        type="primary",
        use_container_width=True,
        disabled=is_job_running
    )

with col_btn2:
    if is_job_paused:
        pause_resume_clicked = st.button("▶️ Reprendre", type="secondary", use_container_width=True)
    else:
        pause_resume_clicked = st.button("⏸️ Pause", type="secondary", use_container_width=True, disabled=not is_job_running)

with col_btn3:
    stop_clicked = st.button(
        "🛑 Arrêter",
        type="secondary",
        use_container_width=True,
        disabled=not is_job_running
    )

with col_btn4:
    reset_clicked = st.button(
        "🔄 Réinitialiser",
        type="secondary",
        use_container_width=True,
        disabled=is_job_running
    )

if start_clicked and not is_job_running:
    pipeline_worker.start_job(
        companies=companies_list,
        job_titles=titles_list,
        location=location_val,
        max_profiles_per_search=max_contacts_val
    )
    show_toast("Job de prospection démarré en arrière-plan !", icon="🚀")
    st.rerun()

if pause_resume_clicked and is_job_running:
    if is_job_paused:
        if hasattr(pipeline_worker, "resume_job"):
            pipeline_worker.resume_job()
        else:
            pipeline_worker._is_paused = False
            pipeline_worker._current_status = "▶️ Reprise de la prospection..."
        show_toast("Reprise de la prospection.", icon="▶️")
    else:
        if hasattr(pipeline_worker, "pause_job"):
            pipeline_worker.pause_job()
        else:
            pipeline_worker._is_paused = True
            pipeline_worker._current_status = "⏸️ Prospection en pause..."
        show_toast("Prospection mise en pause.", icon="⏸️")
    st.rerun()

if stop_clicked and is_job_running:
    if hasattr(pipeline_worker, "stop_job"):
        pipeline_worker.stop_job()
    else:
        pipeline_worker._should_stop = True
        pipeline_worker._current_status = "Arrêt d'urgence..."
    show_toast("Arrêt immédiat en cours...", icon="🛑")
    st.rerun()

if reset_clicked and not is_job_running:
    if hasattr(pipeline_worker, "reset_job"):
        pipeline_worker.reset_job()
    else:
        pipeline_worker._progress = 0.0
        pipeline_worker._current_status = "Prêt"
        pipeline_worker._logs = []
        pipeline_worker._recent_leads = []
        pipeline_worker._total_saved = 0
        pipeline_worker._error = None
    show_toast("État réinitialisé avec succès.", icon="🔄")
    st.rerun()

# Affichage du statut en cours
if is_job_running or worker_status["logs"]:
    st.markdown("### ⚡ Activité en Temps Réel")
    
    pct = worker_status["progress"]
    msg = worker_status["current_status"]
    st.progress(pct, text=f"{int(pct * 100)}% — {msg}")

    if is_job_running:
        st.info(f"📍 **Action en cours :** {msg}")
    elif worker_status.get("error"):
        st.error(f"❌ **Erreur :** {worker_status['error']}")
    else:
        st.success(f"🎉 **Prospection terminée avec succès !** {msg}")
        if pct >= 0.95 and ("job_celebrated" not in st.session_state or not st.session_state["job_celebrated"]):
            st.balloons()
            st.session_state["job_celebrated"] = True

    # Console de logs en direct
    logs = worker_status["logs"]
    if logs:
        st.markdown("##### 📜 Journal d'Exécution en Direct")
        st.code("\n".join(logs[-10:]), language="log")

    # Tableau dynamique des contacts extraits pendant cette session (10 par 10)
    recent_leads = worker_status.get("recent_leads", [])
    if recent_leads:
        st.markdown(f"##### 👤 Contacts Trouvés en Temps Réel dans cette Session ({len(recent_leads)})")
        cols_live = ["first_name", "last_name", "job_title", "company", "proposed_email", "confidence_score", "status"]
        df_live = pd.DataFrame(recent_leads)
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

    # Rafraîchissement automatique de la page tant que le job tourne
    if is_job_running:
        time.sleep(1.5)
        st.rerun()

# Affichage permanent des derniers contacts dans la base de données (10 par 10)
st.markdown("<hr style='margin: 25px 0; border-color: #E0E4E8;'/>", unsafe_allow_html=True)
st.markdown("### 📋 10 Derniers Contacts Enregistrés dans la Base SQLite")
recent_df = get_recent_leads(limit=10)
if not recent_df.empty:
    st.dataframe(
        recent_df,
        column_config={
            "first_name": "Prénom",
            "last_name": "Nom",
            "job_title": "Poste",
            "company": "Entreprise",
            "proposed_email": "Email (Proposé)",
            "confidence_score": st.column_config.ProgressColumn(
                "Confiance",
                format="%d%%",
                min_value=0,
                max_value=100
            ),
            "status": "Statut MX",
            "profile_url": st.column_config.LinkColumn("Profil LinkedIn", display_text="Ouvrir")
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Aucun contact pour le moment. Cliquez sur '🚀 Lancer la Prospection' ci-dessus.")
