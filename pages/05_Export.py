"""
Page 05 - Exportation et Téléchargement des Données.
Permet d'exporter en Excel (.xlsx) stylisé ou CSV avec sélection sur-mesure des colonnes.
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

from components.sidebar import render_sidebar
from storage.db_manager import db_manager
from utils.data_processor import clean_and_deduplicate_database, get_all_leads_df
from utils.export_helper import generate_csv_bytes, generate_excel_bytes
from utils.state_manager import init_session_state

try:
    st.set_page_config(
    page_title="Export | LinkedIn Prospector V3.1",
    page_icon="📤",
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

st.title("📤 Exportation des Contacts")
st.markdown("Générez et téléchargez votre fichier de contacts pour vos campagnes de candidature de stage.")

from core.worker.pipeline_worker import pipeline_worker
import pandas as pd

worker_status = pipeline_worker.get_status()
session_leads = worker_status.get("recent_leads", [])
df_all = get_all_leads_df()

if session_leads:
    st.markdown(
        f"""
        <div style="background: #E8F0FE; border-left: 4px solid #1967D2; padding: 10px 16px; border-radius: 6px; margin-bottom: 14px;">
            <strong style="color: #1967D2;">🎯 Session en Cours Détectée :</strong> <b>{len(session_leads)} contact(s)</b> qualifiés dans cette session.
        </div>
        """,
        unsafe_allow_html=True
    )
    scope_choice = st.radio(
        "Périmètre à exporter :",
        [f"⚡ Contacts de cette Session ({len(session_leads)} contacts)", f"🗄️ Tous les contacts (Base cumulée : {len(df_all)} contacts)"],
        index=0,
        horizontal=True
    )
    if "Session" in scope_choice:
        df = pd.DataFrame(session_leads)
    else:
        df = df_all
else:
    df = df_all

if df.empty:
    st.info("Aucun contact disponible pour l'export. Lancez une prospection pour alimenter la session.")
else:
    exp_col1, exp_col2 = st.columns([4, 6])

    with exp_col1:
        st.markdown("### ⚙️ Options du Fichier")
        
        file_format = st.radio("Format de sortie :", ["Excel (.xlsx) stylisé", "CSV (.csv point-virgule)"])

        # Actions de nettoyage et d'audit
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("🧹 Dédupliquer", help="Supprime les doublons résiduels et conserve la meilleure version de chaque contact", use_container_width=True):
                from utils.data_processor import clean_and_deduplicate_database
                from components.notifications import show_toast
                removed = clean_and_deduplicate_database()
                if removed > 0:
                    show_toast(f"{removed} doublon(s) purgé(s) !", icon="✨")
                else:
                    show_toast("Aucun doublon, base parfaitement saine.", icon="✅")
                st.rerun()

        with btn_c2:
            if st.button("✨ Re-Vérification Finale", help="Re-vérifie chaque personne et chaque email via les serveurs MX DNS et met à jour les scores", type="primary", use_container_width=True):
                with st.spinner("🔍 Audit approfondi : Re-vérification lead par lead & email par email en cours..."):
                    from utils.data_processor import deep_verify_all_leads_process
                    from components.notifications import show_toast
                    stats = deep_verify_all_leads_process()
                show_toast(f"Audit terminé : {stats.get('verified', 0)} contact(s) vérifié(s) et actualisé(s) !", icon="🎯")
                st.rerun()

        status_filter = st.selectbox(
            "Filtrer par statut avant export :",
            ["Tous les contacts", "Emails Validés uniquement (Recommandé)", "À vérifier", "Non vérifiables"]
        )

        all_columns = list(df.columns)
        default_columns = [
            "first_name", "last_name", "job_title", "company",
            "proposed_email", "alt_email_1", "alt_email_2",
            "confidence_score", "status", "mx_verified", "profile_url", "matched_keywords"
        ]
        chosen_defaults = [c for c in default_columns if c in all_columns]

        st.markdown("**Colonnes à inclure :**")
        selected_cols = st.multiselect(
            "Sélectionnez les champs :",
            options=all_columns,
            default=chosen_defaults
        )

    export_df = df.copy()
    if status_filter == "Emails Validés uniquement (Recommandé)":
        export_df = export_df[export_df["status"].astype(str).str.startswith("Validé") | (export_df["mx_verified"].astype(str).str.lower() == "oui")]
    elif status_filter == "À vérifier":
        export_df = export_df[export_df["status"].astype(str).str.contains("À vérifier")]
    elif status_filter == "Non vérifiables":
        export_df = export_df[export_df["status"].astype(str).str.contains("Non vérifiable|Invalide")]

    with exp_col2:
        st.markdown("### 📥 Téléchargement Immédiat")
        st.caption(f"**{len(export_df)}** contact(s) prêts pour l'exportation.")

        if not export_df.empty:
            if "Excel" in file_format:
                excel_bytes = generate_excel_bytes(export_df, selected_columns=selected_cols)
                st.download_button(
                    label=f"📊 Télécharger contacts_stage.xlsx ({len(export_df)} lignes)",
                    data=excel_bytes,
                    file_name="contacts_stage.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
            else:
                csv_bytes = generate_csv_bytes(export_df, selected_columns=selected_cols)
                st.download_button(
                    label=f"📄 Télécharger contacts_stage.csv ({len(export_df)} lignes)",
                    data=csv_bytes,
                    file_name="contacts_stage.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )

        st.markdown("<hr style='margin: 16px 0; border-color: #E0E4E8;'/>", unsafe_allow_html=True)
        st.markdown("### 👁️ Prévisualisation des données")
        if not export_df.empty and selected_cols:
            st.dataframe(export_df[selected_cols].head(10), use_container_width=True, hide_index=True)
        else:
            st.warning("Aucune donnée correspondant aux critères sélectionnés.")

    # Section Historique & Archives des Missions Précédentes (Style Apollo/Waalaxy)
    st.markdown("<hr style='margin: 24px 0; border-color: #E0E4E8;'/>", unsafe_allow_html=True)
    st.markdown("### 📁 Historique des Missions & Archives Précédentes")
    st.caption("Consultez et téléchargez à tout moment les fichiers Excel de chacune de vos prospections passées.")

    from utils.export_helper import get_export_history
    history_items = get_export_history()

    if history_items:
        for idx, item in enumerate(history_items[:10]):
            c_info, c_btn = st.columns([7, 3])
            with c_info:
                st.markdown(f"📦 **{item['filename']}** &nbsp;•&nbsp; 📅 *{item['date']}* &nbsp;•&nbsp; `{item['size_kb']} Ko`")
            with c_btn:
                try:
                    with open(item["filepath"], "rb") as hf:
                        file_bytes = hf.read()
                    st.download_button(
                        label="⬇️ Télécharger",
                        data=file_bytes,
                        file_name=item["filename"],
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"hist_dl_{idx}_{item['filename']}",
                        use_container_width=True
                    )
                except Exception:
                    pass
    else:
        st.info("Aucune archive précédente pour l'instant. Vos prochains exports y seront automatiquement conservés.")
