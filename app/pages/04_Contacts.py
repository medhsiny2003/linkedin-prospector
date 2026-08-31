"""
Page 04 - Visualisation, Filtrage et Gestion des Contacts.
Recherche textuelle multi-colonnes, filtres par entreprise/statut, et actions groupées.
"""

import sys
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = Path(__file__).resolve().parent.parent
for p in [str(PROJECT_ROOT), str(APP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from components.notifications import show_toast
from components.sidebar import render_sidebar
from utils.data_processor import delete_leads, get_all_leads_df
from utils.export_helper import generate_excel_bytes
from utils.state_manager import init_session_state

st.set_page_config(
    page_title="Contacts | LinkedIn Prospector V3.1",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Chargement du style CSS
css_path = APP_DIR / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session_state()
render_sidebar()

st.title("📋 Répertoire des Contacts")
st.markdown("Consultez, filtrez et gérez les contacts RH et recruteurs identifiés.")

df = get_all_leads_df()

if df.empty:
    st.info("Aucun contact enregistré dans la base de données. Lancez une recherche depuis l'onglet **Prospection** !")
else:
    # --- FILTRES ---
    st.markdown("### 🔍 Filtres de Recherche")
    f_col1, f_col2, f_col3 = st.columns([3, 2, 3])

    # 1. Filtre Entreprise
    unique_companies = sorted(list(df["company"].dropna().unique()))
    with f_col1:
        selected_companies = st.multiselect(
            "Filtrer par entreprise :",
            options=unique_companies,
            default=[]
        )

    # 2. Filtre Statut Email
    with f_col2:
        status_options = ["Tous les statuts", "Validé", "À vérifier", "Non vérifiable"]
        selected_status = st.selectbox("Statut de validation :", status_options)

    # 3. Recherche textuelle globale
    with f_col3:
        search_query = st.text_input("Recherche textuelle (Nom, Poste, Email...) :", placeholder="Ex: Thales, Recruteur, dupont...")

    from enricher.lead_scorer import lead_scorer

    def compute_row_score(row):
        score, stars, _ = lead_scorer.calculate_score(row.to_dict())
        return stars, score

    if not df.empty:
        df[["priority", "score"]] = df.apply(compute_row_score, axis=1, result_type="expand")

    # Application des filtres
    filtered_df = df.copy()

    if selected_companies:
        filtered_df = filtered_df[filtered_df["company"].isin(selected_companies)]

    if selected_status != "Tous les statuts":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

    if search_query.strip():
        q = search_query.strip().lower()
        filtered_df = filtered_df[
            filtered_df["first_name"].str.lower().str.contains(q, na=False) |
            filtered_df["last_name"].str.lower().str.contains(q, na=False) |
            filtered_df["job_title"].str.lower().str.contains(q, na=False) |
            filtered_df["company"].str.lower().str.contains(q, na=False) |
            filtered_df["proposed_email"].str.lower().str.contains(q, na=False)
        ]

    # Tri par score de pertinence décroissant par défaut
    if "score" in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by="score", ascending=False)

    total_filt = len(filtered_df)
    val_filt = len(filtered_df[filtered_df["status"].astype(str).str.contains("Validé")])
    rate_filt = round((val_filt / total_filt) * 100, 1) if total_filt > 0 else 0.0

    st.caption(f"**{total_filt}** contact(s) qualifié(s) &nbsp;|&nbsp; **{val_filt}** email(s) validé(s) ({rate_filt}%) &nbsp;|&nbsp; Trié par pertinence décroissante")

    display_cols = [
        "id", "priority", "first_name", "last_name", "job_title", "company",
        "proposed_email", "score", "status", "profile_url"
    ]
    
    st.dataframe(
        filtered_df[[c for c in display_cols if c in filtered_df.columns]],
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "priority": st.column_config.TextColumn("Priorité", help="★★★ = Décideur RH/R&D (Recommandé)"),
            "first_name": "Prénom",
            "last_name": "Nom",
            "job_title": "Poste",
            "company": "Entreprise",
            "proposed_email": "Email Proposé",
            "score": st.column_config.ProgressColumn(
                "Pertinence",
                format="%d%%",
                min_value=0,
                max_value=100
            ),
            "status": "Statut MX",
            "profile_url": st.column_config.LinkColumn("Profil LinkedIn", display_text="Ouvrir")
        },
        use_container_width=True,
        hide_index=True,
        height=450
    )

    # --- ACTIONS EN MASSE ---
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("### ⚡ Actions sur la sélection filtrée")
    act_col1, act_col2, _ = st.columns([3, 3, 4])

    with act_col1:
        if not filtered_df.empty:
            excel_bytes = generate_excel_bytes(filtered_df)
            st.download_button(
                label=f"📥 Télécharger la sélection Excel ({total_filt})",
                data=excel_bytes,
                file_name="contacts_selection.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )

    with act_col2:
        if not filtered_df.empty:
            with st.expander("🗑️ Supprimer les contacts filtrés", expanded=False):
                st.warning(f"Êtes-vous sûr de vouloir supprimer définitivement ces {total_filt} contact(s) ?")
                if st.button("Confirmer la suppression", type="secondary"):
                    ids_to_del = filtered_df["id"].tolist()
                    if delete_leads(ids_to_del):
                        show_toast(f"{len(ids_to_del)} contacts supprimés.", icon="🗑️")
                        st.rerun()
                    else:
                        st.error("Erreur lors de la suppression.")
