"""
Barre latérale unifiée pour l'interface Streamlit.
Affiche le logo, les statuts de santé système, le statut du cookie et les quotas de sécurité.
"""

import sys
from pathlib import Path
import streamlit as st

# Resolution universelle et robuste des chemins
current_file = Path(__file__).resolve()
PROJECT_ROOT = None
for parent in [current_file.parent, current_file.parent.parent, current_file.parent.parent.parent]:
    if (parent / "config.py").exists():
        PROJECT_ROOT = parent
        break
if not PROJECT_ROOT:
    PROJECT_ROOT = current_file.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config
from core.auth.cookie_manager import cookie_manager
from core.monitoring.health_check import health_checker
from core.security.warmup_engine import warmup_engine
from storage.db_manager import db_manager


def render_sidebar() -> None:
    """Affiche la barre latérale sur toutes les pages."""
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding-bottom: 8px;">
                <h2 style="color: #0A66C2; margin-bottom: 0;">🎯 Prospector V3.1</h2>
                <span style="font-size: 0.8rem; color: #666666; font-weight: 500;">Assistant Stage Drones & Embarqué</span>
            </div>
            <hr style="margin-top: 0; margin-bottom: 12px; border-color: #E0E4E8;"/>
            """,
            unsafe_allow_html=True
        )

        # 0. Menu de Navigation Interactif Multi-Pages
        st.markdown("### 🧭 Navigation")
        try:
            st.page_link("app.py", label="Tableau de Bord", icon="🏠")
            st.page_link("pages/02_Configuration.py", label="Configuration", icon="⚙️")
            st.page_link("pages/03_Prospection.py", label="Prospection en Direct", icon="📊")
            st.page_link("pages/04_Contacts.py", label="Répertoire Contacts", icon="📋")
            st.page_link("pages/05_Export.py", label="Export Excel / CSV", icon="📤")
            st.page_link("pages/06_Logs.py", label="Journaux & Audit", icon="📜")
        except Exception:
            try:
                st.page_link("app/streamlit_app.py", label="Tableau de Bord", icon="🏠")
                st.page_link("app/pages/02_Configuration.py", label="Configuration", icon="⚙️")
                st.page_link("app/pages/03_Prospection.py", label="Prospection en Direct", icon="📊")
                st.page_link("app/pages/04_Contacts.py", label="Répertoire Contacts", icon="📋")
                st.page_link("app/pages/05_Export.py", label="Export Excel / CSV", icon="📤")
                st.page_link("app/pages/06_Logs.py", label="Journaux & Audit", icon="📜")
            except Exception:
                pass

        st.markdown("<hr style='margin: 12px 0; border-color: #E0E4E8;'/>", unsafe_allow_html=True)

        # 1. Statut du Cookie LinkedIn
        li_at = cookie_manager.extract_li_at_value(config.LINKEDIN_COOKIE)
        if li_at:
            st.success("🔒 Cookie `li_at` configuré", icon="✅")
        else:
            st.warning("⚠️ Cookie `li_at` non configuré", icon="⚠️")

        # 2. Diagnostic Système
        health = health_checker.run_all_checks()
        if health.get("overall_health") == "HEALTHY":
            st.info("🟢 Système opérationnel (DNS & WAL)", icon="🛡️")
        else:
            st.error("🔴 Anomalie système détectée", icon="❌")

        # 3. Quota & Warm-up
        start_date = db_manager.get_or_create_campaign_start_date()
        daily_limit = warmup_engine.calculate_daily_limit(start_date)
        is_working_hour, reason = warmup_engine.is_within_working_hours()

        st.markdown("### 🕒 Sécurité & Warm-Up")
        st.caption(f"**Quota journalier :** {daily_limit} invitations max")
        st.caption("🟢 **Disponibilité :** Prospection 24/7 active (sans limite horaire)")

        # 4. Proxy Résidentiel
        if config.PROXY_URL:
            st.caption("🌐 **Proxy :** Résidentiel activé")
        else:
            st.caption("🌐 **Proxy :** Direct (Box Résidentielle)")

        st.markdown("<hr style='margin: 16px 0; border-color: #E0E4E8;'/>", unsafe_allow_html=True)
        st.caption("🔒 **Sécurité :** Headless désactivé • Validateur MX DNS pur • Logs SHA-256")
