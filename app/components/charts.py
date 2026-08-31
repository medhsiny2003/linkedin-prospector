"""
Composants graphiques interactifs (Plotly) pour l'analyse visuelle des contacts.
"""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_company_bar_chart(df_company: pd.DataFrame) -> None:
    """Affiche le diagramme à barres des contacts par entreprise."""
    if df_company.empty or df_company["count"].sum() == 0:
        st.info("Aucune donnée d'entreprise à afficher pour le moment.")
        return

    fig = px.bar(
        df_company,
        x="company",
        y="count",
        title="<b>Répartition des contacts par entreprise</b>",
        labels={"company": "Entreprise", "count": "Nombre de contacts"},
        color_discrete_sequence=["#0A66C2"],
        text="count"
    )
    fig.update_traces(textposition='outside', marker_line_color='#004182', marker_line_width=1)
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font_family="Inter, sans-serif",
        margin=dict(l=20, r=20, t=50, b=30),
        xaxis_tickangle=-30,
        height=320
    )
    st.plotly_chart(fig, use_container_width=True)


def render_status_donut_chart(df_status: pd.DataFrame) -> None:
    """Affiche le diagramme circulaire (donut) des statuts d'emails."""
    if df_status.empty or df_status["count"].sum() == 0:
        st.info("Aucun statut d'email disponible.")
        return

    color_map = {
        "Validé": "#057642",         # Vert LinkedIn
        "À vérifier": "#E68A00",     # Orange
        "Non vérifiable": "#B92B27"   # Rouge
    }

    fig = px.pie(
        df_status,
        names="status",
        values="count",
        title="<b>Statut de validation des emails (DNS MX)</b>",
        color="status",
        color_discrete_map=color_map,
        hole=0.5
    )
    fig.update_traces(textinfo="percent+label", pull=[0.05, 0, 0])
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font_family="Inter, sans-serif",
        margin=dict(l=20, r=20, t=50, b=30),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig, use_container_width=True)


def render_timeline_chart(df_timeline: pd.DataFrame) -> None:
    """Affiche le graphique chronologique des contacts ajoutés."""
    if df_timeline.empty:
        return

    fig = px.line(
        df_timeline,
        x="date",
        y="count",
        title="<b>Évolution des contacts collectés dans le temps</b>",
        labels={"date": "Date", "count": "Nouveaux contacts"},
        markers=True,
        color_discrete_sequence=["#70B5F9"]
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8, color="#0A66C2"))
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font_family="Inter, sans-serif",
        margin=dict(l=20, r=20, t=50, b=30),
        height=260
    )
    st.plotly_chart(fig, use_container_width=True)
