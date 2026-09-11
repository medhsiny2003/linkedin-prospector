"""
Gestionnaire d'injection CSS et Font Awesome pour Streamlit.
Evite les erreurs de parsing Markdown et garantit un affichage 100% propre.
"""

from pathlib import Path
import streamlit as st

def apply_custom_css(app_dir: Path) -> None:
    """Charge Font Awesome 6 et la feuille de style CSS personnalisée."""
    css_path = app_dir / "styles" / "custom.css"
    css_content = ""
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
    
    html_block = f"""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
    {css_content}
    </style>
    """
    
    # Utilisation de st.html (Streamlit 1.35+) ou st.markdown propre
    if hasattr(st, "html"):
        st.html(html_block)
    else:
        st.markdown(html_block, unsafe_allow_html=True)