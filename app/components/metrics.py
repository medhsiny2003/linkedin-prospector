"""
Composant de rendu des métriques clés (KPIs) pour le tableau de bord.
"""

from typing import Any, Dict, Optional
import streamlit as st


def render_kpi_cards(kpi_data: Dict[str, Any], session_data: Optional[Dict[str, Any]] = None) -> None:
    """Affiche les 4 cartes de métriques principales (Session active ou Total base)."""
    col1, col2, col3, col4 = st.columns(4)

    if session_data and (session_data.get("is_running") or session_data.get("session_count", 0) > 0):
        # Affichage focalisé sur la Session en Cours (repart à 0 à chaque nouvelle session)
        sess_count = session_data.get("session_count", 0)
        sess_valid = session_data.get("session_valid", 0)
        sess_comps = session_data.get("session_companies", 0)
        sess_status = session_data.get("status_label", "⚡ En direct")

        with col1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">👤 Contacts Session</div>
                    <div class="metric-value" style="color: #1967D2;">{sess_count}</div>
                    <div class="metric-delta neutral">Total base : {kpi_data['total_contacts']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">🏢 Entreprises Session</div>
                    <div class="metric-value">{sess_comps}</div>
                    <div class="metric-delta neutral">Cibles traitées</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">✉️ Emails Validés Session</div>
                    <div class="metric-value" style="color: #057642;">{sess_valid}</div>
                    <div class="metric-delta positive">Validation MX en direct</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">⏱️ Statut Session</div>
                    <div class="metric-value" style="font-size: 1.15rem; padding-top: 8px; color: #1967D2;">{sess_status}</div>
                    <div class="metric-delta neutral">{kpi_data['last_execution']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        # Affichage classique global
        with col1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">👥 Total Contacts</div>
                    <div class="metric-value">{kpi_data['total_contacts']}</div>
                    <div class="metric-delta neutral">Enregistrés dans la base</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">🏢 Entreprises</div>
                    <div class="metric-value">{kpi_data['total_companies']}</div>
                    <div class="metric-delta neutral">Cibles identifiées</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col3:
            rate = kpi_data['validation_rate']
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">✉️ Emails Validés</div>
                    <div class="metric-value" style="color: #057642;">{kpi_data['validated_emails']}</div>
                    <div class="metric-delta positive">Taux de succès : {rate}%</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">⏱️ Dernière Activité</div>
                    <div class="metric-value" style="font-size: 1.25rem; padding-top: 8px;">{kpi_data['last_execution']}</div>
                    <div class="metric-delta neutral">Dernière synchronisation</div>
                </div>
                """,
                unsafe_allow_html=True
            )
