"""
Composant de rendu des métriques clés (KPIs) pour le tableau de bord.
"""

from typing import Any, Dict, Optional
import streamlit as st


def render_kpi_cards(kpi_data: Dict[str, Any], session_data: Optional[Dict[str, Any]] = None) -> None:
    """Affiche les 4 cartes de métriques principales avec Font Awesome 6 et le Design System Pro."""
    col1, col2, col3, col4 = st.columns(4)

    if session_data and (session_data.get("is_running") or session_data.get("session_count", 0) > 0):
        sess_count = session_data.get("session_count", 0)
        sess_valid = session_data.get("session_valid", 0)
        sess_comps = session_data.get("session_companies", 0)
        sess_status = session_data.get("status_label", "⚡ En direct")

        with col1:
            st.markdown(
                f"""
                <div class="kpi-card kpi-blue">
                    <div class="kpi-header">
                        <span class="kpi-title">Contacts Session</span>
                        <div class="kpi-icon blue"><i class="fa-solid fa-user-plus"></i></div>
                    </div>
                    <div class="kpi-value">{sess_count}</div>
                    <div class="kpi-subtitle">Total base : <strong>{kpi_data['total_contacts']}</strong></div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"""
                <div class="kpi-card kpi-purple">
                    <div class="kpi-header">
                        <span class="kpi-title">Entreprises Session</span>
                        <div class="kpi-icon purple"><i class="fa-solid fa-building"></i></div>
                    </div>
                    <div class="kpi-value">{sess_comps}</div>
                    <div class="kpi-subtitle">Cibles traitées en direct</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                f"""
                <div class="kpi-card kpi-green">
                    <div class="kpi-header">
                        <span class="kpi-title">Emails Validés</span>
                        <div class="kpi-icon green"><i class="fa-solid fa-envelope-circle-check"></i></div>
                    </div>
                    <div class="kpi-value">{sess_valid}</div>
                    <div class="kpi-subtitle">Certifiés MX DNS</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col4:
            st.markdown(
                f"""
                <div class="kpi-card kpi-amber">
                    <div class="kpi-header">
                        <span class="kpi-title">Statut Moteur</span>
                        <div class="kpi-icon amber"><i class="fa-solid fa-bolt"></i></div>
                    </div>
                    <div class="kpi-value" style="font-size: 1.3rem; padding-top: 6px;">{sess_status}</div>
                    <div class="kpi-subtitle">{kpi_data['last_execution']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        with col1:
            st.markdown(
                f"""
                <div class="kpi-card kpi-blue">
                    <div class="kpi-header">
                        <span class="kpi-title">Total Contacts</span>
                        <div class="kpi-icon blue"><i class="fa-solid fa-users"></i></div>
                    </div>
                    <div class="kpi-value">{kpi_data['total_contacts']}</div>
                    <div class="kpi-subtitle">Prospects qualifiés en base</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"""
                <div class="kpi-card kpi-purple">
                    <div class="kpi-header">
                        <span class="kpi-title">Entreprises Ciblées</span>
                        <div class="kpi-icon purple"><i class="fa-solid fa-city"></i></div>
                    </div>
                    <div class="kpi-value">{kpi_data['total_companies']}</div>
                    <div class="kpi-subtitle">Sociétés technologiques</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                f"""
                <div class="kpi-card kpi-green">
                    <div class="kpi-header">
                        <span class="kpi-title">Emails Vérifiés</span>
                        <div class="kpi-icon green"><i class="fa-solid fa-circle-check"></i></div>
                    </div>
                    <div class="kpi-value">{kpi_data['validated_emails']}</div>
                    <div class="kpi-subtitle">{kpi_data['validation_rate']}% taux de validité</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col4:
            st.markdown(
                f"""
                <div class="kpi-card kpi-amber">
                    <div class="kpi-header">
                        <span class="kpi-title">Dernière Action</span>
                        <div class="kpi-icon amber"><i class="fa-solid fa-clock-rotate-left"></i></div>
                    </div>
                    <div class="kpi-value" style="font-size: 1.15rem; padding-top: 6px;">{kpi_data['last_execution']}</div>
                    <div class="kpi-subtitle">Horodatage certifié</div>
                </div>
                """,
                unsafe_allow_html=True
            )
