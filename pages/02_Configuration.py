"""
Page 02 - Configuration des recherches, authentification et profils sauvegardés.
"""

import sys
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

from components.notifications import show_toast
from components.sidebar import render_sidebar
from config import config
from core.auth.cookie_manager import cookie_manager
from utils.state_manager import (
    delete_profile,
    get_active_config,
    get_saved_profiles,
    init_session_state,
    save_active_config,
    save_profile
)

try:
    st.set_page_config(
    page_title="Configuration | LinkedIn Prospector V3.1",
    page_icon="⚙️",
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

st.title("⚙️ Paramètres & Configuration")
st.markdown("Personnalisez vos critères de ciblage pour votre recherche de stage ou alternance.")

# --- SECTION 3 : Profils enregistrés (en haut pour charger rapidement) ---
st.markdown("### 💾 Profils de Recherche Sauvegardés")
profiles = get_saved_profiles()
profile_names = list(profiles.keys())

active_cfg = get_active_config()
active_prof_name = st.session_state.get("selected_profile", active_cfg.get("selected_profile", profile_names[0] if profile_names else ""))

p_col1, p_col2, p_col3 = st.columns([4, 2, 2])

with p_col1:
    selected_p = st.selectbox(
        "Sélectionner un profil préconfiguré :",
        profile_names,
        index=profile_names.index(active_prof_name) if active_prof_name in profile_names else 0
    )

with p_col2:
    if st.button("📥 Charger ce profil", use_container_width=True):
        p_data = profiles[selected_p]
        comp_val = p_data.get("companies", "")
        jobs_val = p_data.get("job_titles", "")
        loc_val = p_data.get("location", "Maroc")
        max_c = p_data.get("max_contacts", 20)

        st.session_state["companies"] = comp_val
        st.session_state["job_titles"] = jobs_val
        st.session_state["location"] = loc_val
        st.session_state["max_contacts"] = max_c
        st.session_state["selected_profile"] = selected_p

        save_active_config({
            "selected_profile": selected_p,
            "companies": comp_val,
            "job_titles": jobs_val,
            "location": loc_val,
            "max_contacts": max_c
        })
        show_toast(f"Profil '{selected_p}' chargé et activé pour la prospection !", icon="✅")
        st.rerun()

with p_col3:
    if not selected_p.startswith("🇲🇦") and not selected_p.startswith("🇫🇷"):
        if st.button("🗑️ Supprimer", use_container_width=True):
            delete_profile(selected_p)
            show_toast(f"Profil '{selected_p}' supprimé.", icon="🗑️")
            st.rerun()

st.markdown("<hr style='margin: 16px 0; border-color: #E0E4E8;'/>", unsafe_allow_html=True)

# --- SECTION 1 : Formulaire de Recherche ---
st.markdown("### 🎯 Critères de Ciblage")

col_form1, col_form2 = st.columns(2)

with col_form1:
    companies_input = st.text_area(
        "🏢 Entreprises ciblées (séparées par des virgules) :",
        value=st.session_state.get("companies", active_cfg.get("companies", "")),
        height=120,
        help="Ex: OCP Group, Safran Maroc, Airbus Atlantic Maroc, Capgemini Maroc, Thales"
    )

with col_form2:
    titles_input = st.text_area(
        "💼 Postes / Mots-clés recherchés (séparés par des virgules) :",
        value=st.session_state.get("job_titles", active_cfg.get("job_titles", "")),
        height=120,
        help="Ex: Responsable RH, Talent Acquisition, Chef de projet Drones, Ingénieur Systèmes Embarqués"
    )

# --- SECTION 2 : Localisation Géographique ---
st.markdown("#### 📍 Localisation & Zone Géographique Ciblée")

LOCATION_PRESETS = {
    "🇲🇦 Maroc (Tout le pays)": "Maroc",
    "🇲🇦 Maroc - Casablanca & Nouaceur (Midparc / Aéro & Tech)": "Casablanca, Nouaceur, Maroc",
    "🇲🇦 Maroc - Rabat, Salé & Kénitra (R&D / Instituts / ESN)": "Rabat, Salé, Kénitra, Maroc",
    "🇲🇦 Maroc - Tanger & Tétouan (Tanger Tech / Automobile & Aéro)": "Tanger, Tétouan, Maroc",
    "🇲🇦 Maroc - Marrakech, Fès, Agadir & Oujda": "Marrakech, Fès, Agadir, Oujda, Maroc",
    "🇫🇷 France (Toute la France)": "France",
    "🇫🇷 France - Paris & Île-de-France": "Paris, Île-de-France, France",
    "🇫🇷 France - Toulouse & Occitanie (Aéro & Spatial)": "Toulouse, Occitanie, France",
    "🇫🇷 France - Lyon & Auvergne-Rhône-Alpes": "Lyon, Auvergne-Rhône-Alpes, France",
    "🇫🇷 France - Bordeaux & Nouvelle-Aquitaine": "Bordeaux, Nouvelle-Aquitaine, France",
    "🌐 International / Monde Entier": "International",
    "✍️ Personnalisé / Saisie libre": "custom"
}

loc_preset_labels = list(LOCATION_PRESETS.keys())
current_loc_val = st.session_state.get("location", active_cfg.get("location", "Maroc"))

# Trouver l'index par défaut correspondant à la valeur actuelle
preset_idx = 0
for idx, (label, val) in enumerate(LOCATION_PRESETS.items()):
    if val != "custom" and (val.lower() == current_loc_val.lower() or current_loc_val.lower() in val.lower()):
        preset_idx = idx
        break
else:
    preset_idx = len(loc_preset_labels) - 1  # Personnalisé

loc_col1, loc_col2 = st.columns([1, 1])

with loc_col1:
    selected_loc_preset = st.selectbox(
        "Sélectionnez une zone géographique prédéfinie :",
        loc_preset_labels,
        index=preset_idx,
        help="Choisissez un hub économique ou un pays pour calibrer automatiquement votre recherche LinkedIn & X-Ray."
    )

with loc_col2:
    if selected_loc_preset != "✍️ Personnalisé / Saisie libre":
        suggested_val = LOCATION_PRESETS[selected_loc_preset]
        location_input = st.text_input(
            "Valeur envoyée au moteur de recherche :",
            value=suggested_val,
            help="Vous pouvez modifier cette valeur pour affiner (ex: Casablanca, Nouaceur)."
        )
    else:
        location_input = st.text_input(
            "Saisie personnalisée de la localisation :",
            value=current_loc_val,
            placeholder="Ex: Casablanca, Rabat, Toulouse, Paris, Canada...",
            help="Saisissez les villes ou pays de votre choix séparés par des virgules."
        )

# Options Avancées (Expandable)
with st.expander("🛠️ Options Avancées & Filtres", expanded=False):
    opt_col1, opt_col2, opt_col3 = st.columns(3)
    with opt_col1:
        max_contacts_slider = st.slider(
            "Limite de profils par recherche :",
            min_value=5,
            max_value=50,
            value=st.session_state.get("max_contacts", active_cfg.get("max_contacts", 20)),
            step=5
        )
    with opt_col2:
        enable_mx_toggle = st.toggle("Activer la vérification MX DNS", value=st.session_state.get("enable_mx", active_cfg.get("enable_mx", True)))
    with opt_col3:
        safe_mode_toggle = st.toggle("Mode Sécurisé (Délais stricts & Warm-up)", value=st.session_state.get("safe_mode", active_cfg.get("safe_mode", True)))

# Synchronisation dans le session_state
st.session_state["companies"] = companies_input
st.session_state["job_titles"] = titles_input
st.session_state["location"] = location_input
st.session_state["max_contacts"] = max_contacts_slider
st.session_state["enable_mx"] = enable_mx_toggle
st.session_state["safe_mode"] = safe_mode_toggle

# Actions de Sauvegarde et d'Application
col_act1, col_act2 = st.columns([1, 1])

with col_act1:
    if st.button("🚀 Appliquer pour la Prospection", type="primary", use_container_width=True):
        save_active_config({
            "selected_profile": selected_p,
            "companies": companies_input,
            "job_titles": titles_input,
            "location": location_input,
            "max_contacts": max_contacts_slider,
            "enable_mx": enable_mx_toggle,
            "safe_mode": safe_mode_toggle
        })
        show_toast("Configuration activée pour la prospection !", icon="🚀")
        st.rerun()

with col_act2:
    if st.button(f"💾 Enregistrer les modifications dans '{selected_p}'", use_container_width=True):
        save_profile(selected_p, {
            "companies": companies_input,
            "job_titles": titles_input,
            "location": location_input,
            "max_contacts": max_contacts_slider
        })
        save_active_config({
            "selected_profile": selected_p,
            "companies": companies_input,
            "job_titles": titles_input,
            "location": location_input,
            "max_contacts": max_contacts_slider,
            "enable_mx": enable_mx_toggle,
            "safe_mode": safe_mode_toggle
        })
        show_toast(f"Modifications enregistrées dans le profil '{selected_p}' !", icon="💾")
        st.rerun()

# Créer et Ajouter un Nouveau Profil
st.markdown("<br/>", unsafe_allow_html=True)
with st.expander("➕ Créer et Ajouter un Nouveau Profil (avec un nouveau nom)", expanded=False):
    save_col1, save_col2 = st.columns([3, 1])
    with save_col1:
        new_profile_name = st.text_input("Nom du nouveau profil :", placeholder="Ex: Mon Profil Électrotechnique Maroc...")
    with save_col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Ajouter ce profil", use_container_width=True):
            if new_profile_name.strip():
                prof_name = new_profile_name.strip()
                save_profile(prof_name, {
                    "companies": companies_input,
                    "job_titles": titles_input,
                    "location": location_input,
                    "max_contacts": max_contacts_slider
                })
                st.session_state["selected_profile"] = prof_name
                st.session_state["companies"] = companies_input
                st.session_state["job_titles"] = titles_input
                st.session_state["location"] = location_input
                st.session_state["max_contacts"] = max_contacts_slider

                save_active_config({
                    "selected_profile": prof_name,
                    "companies": companies_input,
                    "job_titles": titles_input,
                    "location": location_input,
                    "max_contacts": max_contacts_slider,
                    "enable_mx": enable_mx_toggle,
                    "safe_mode": safe_mode_toggle
                })
                show_toast(f"Nouveau profil '{prof_name}' créé et activé !", icon="✅")
                st.rerun()
            else:
                st.warning("Veuillez renseigner un nom pour le nouveau profil.")

st.markdown("<hr style='margin: 16px 0; border-color: #E0E4E8;'/>", unsafe_allow_html=True)

# --- SECTION 2 : Gestion du Compte LinkedIn & Cookie ---
st.markdown("### 🔒 Authentification & Cookie LinkedIn")

li_cookie = cookie_manager.extract_li_at_value(config.LINKEDIN_COOKIE)
auth_col1, auth_col2 = st.columns([3, 3])

with auth_col1:
    if li_cookie:
        st.success(f"✅ Cookie `li_at` valide et détecté ({len(li_cookie)} caractères)")
        st.caption(f"Empreinte : `{li_cookie[:12]}...{li_cookie[-6:]}`")
    else:
        st.error("❌ Aucun cookie `li_at` détecté dans `.env`.")
        st.info("Ajoutez `LINKEDIN_COOKIE=AQED...` dans le fichier `.env` pour une connexion instantanée.")

with auth_col2:
    st.markdown(
        """
        <div style="background: #F3F6F8; padding: 12px 16px; border-radius: 8px; font-size: 0.85rem;">
            <strong>Comment récupérer votre cookie ?</strong><br/>
            1. Ouvrez LinkedIn sur Microsoft Edge avec votre compte dédié.<br/>
            2. Appuyez sur <code>F12</code> > <strong>Application</strong> (ou Stockage) > <strong>Cookies</strong>.<br/>
            3. Copiez la valeur du cookie <strong>li_at</strong> et collez-la dans <code>.env</code>.
        </div>
        """,
        unsafe_allow_html=True
    )
