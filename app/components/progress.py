"""
Composant de suivi en temps réel de la progression de la prospection.
"""

from typing import Optional
import streamlit as st


def render_progress_panel(
    progress: float,
    status_text: str,
    elapsed_time_sec: Optional[float] = None,
    total_found: int = 0
) -> None:
    """Affiche la jauge de progression et les indicateurs dynamiques."""
    clamped_progress = min(max(progress, 0.0), 1.0)
    st.progress(clamped_progress, text=f"Progression : {int(clamped_progress * 100)}% — {status_text}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Statut", status_text if len(status_text) < 25 else status_text[:22] + "...")
    with col2:
        st.metric("Contacts Détectés", f"{total_found}")
    with col3:
        if elapsed_time_sec:
            mins, secs = divmod(int(elapsed_time_sec), 60)
            st.metric("Temps Écoulé", f"{mins:02d}:{secs:02d}")
        else:
            st.metric("Temps Écoulé", "00:00")
