"""
Système de notifications visuelles, alertes de sécurité et messages Toast.
"""

from typing import Optional
import streamlit as st


def show_toast(message: str, icon: Optional[str] = "ℹ️") -> None:
    """Affiche un message toast éphémère."""
    st.toast(message, icon=icon)


def show_security_banner() -> None:
    """Affiche la bannière d'avertissement de sécurité et de conformité compte dédié."""
    st.markdown(
        """
        <div class="security-card">
            <strong>⚠️ Recommandation Sécurité :</strong> Utilisez impérativement un compte LinkedIn dédié distinct de votre profil personnel.
            Le moteur respecte automatiquement les quotas de warm-up (max 20/jour) et s'exécute toujours avec affichage du navigateur (mode visible).
        </div>
        """,
        unsafe_allow_html=True
    )
