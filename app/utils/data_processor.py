"""
Processeur de données et agrégateur analytique pour l'interface Streamlit.
Fait le pont entre SQLite (db_manager) et les composants visuels Pandas / Plotly.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

# Résolution universelle du chemin racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from storage.db_manager import db_manager


def get_all_leads_df() -> pd.DataFrame:
    """Récupère l'intégralité des leads stockés sous la forme d'un DataFrame Pandas."""
    leads = db_manager.get_all_leads()
    if not leads:
        return pd.DataFrame(columns=[
            "id", "first_name", "last_name", "job_title", "company", "profile_url",
            "proposed_email", "alt_email_1", "alt_email_2", "confidence_score",
            "status", "mx_verified", "matched_keywords", "created_at", "updated_at"
        ])
    df = pd.DataFrame(leads)
    return df


def get_kpi_metrics() -> Dict[str, Any]:
    """Calcule les 4 indicateurs clés de performance (KPIs) pour le tableau de bord."""
    df = get_all_leads_df()
    total_leads = len(df)

    if total_leads == 0:
        return {
            "total_contacts": 0,
            "total_companies": 0,
            "validated_emails": 0,
            "validation_rate": 0.0,
            "last_execution": "Aucune exécution"
        }

    distinct_companies = df["company"].replace("", pd.NA).dropna().nunique()
    validated_mask = df["status"].astype(str).str.startswith("Validé") | (df["mx_verified"].astype(str).str.lower() == "oui")
    validated_count = len(df[validated_mask])
    validation_rate = round((validated_count / total_leads) * 100, 1) if total_leads > 0 else 0.0

    # Date de dernière activité : prend la date de mise à jour la plus récente (updated_at ou created_at)
    latest_ts = None
    if "updated_at" in df.columns and not df["updated_at"].isna().all():
        latest_ts = df["updated_at"].dropna().max()
    elif "created_at" in df.columns and not df["created_at"].isna().all():
        latest_ts = df["created_at"].dropna().max()

    if latest_ts:
        try:
            clean_ts = str(latest_ts).replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            last_exec_str = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            last_exec_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    else:
        last_exec_str = "N/A"

    return {
        "total_contacts": total_leads,
        "total_companies": distinct_companies,
        "validated_emails": validated_count,
        "validation_rate": validation_rate,
        "last_execution": last_exec_str
    }


def get_company_distribution(limit: int = 8) -> pd.DataFrame:
    """Retourne la répartition du nombre de contacts par entreprise (Top N)."""
    df = get_all_leads_df()
    if df.empty or "company" not in df.columns:
        return pd.DataFrame(columns=["company", "count"])

    counts = df["company"].replace("", "Non spécifié").value_counts().reset_index()
    counts.columns = ["company", "count"]
    return counts.head(limit)


def get_status_distribution() -> pd.DataFrame:
    """Retourne la répartition des statuts de validation d'emails."""
    df = get_all_leads_df()
    if df.empty or "status" not in df.columns:
        return pd.DataFrame({"status": ["Validé", "À vérifier", "Non vérifiable"], "count": [0, 0, 0]})

    counts = df["status"].value_counts().reset_index()
    counts.columns = ["status", "count"]
    return counts


def get_timeline_distribution() -> pd.DataFrame:
    """Retourne l'évolution temporelle des contacts ajoutés."""
    df = get_all_leads_df()
    if df.empty or "created_at" not in df.columns:
        return pd.DataFrame(columns=["date", "count"])

    try:
        df["date"] = pd.to_datetime(df["created_at"]).dt.date
        timeline = df.groupby("date").size().reset_index(name="count")
        return timeline.sort_values("date")
    except Exception:
        return pd.DataFrame(columns=["date", "count"])


def get_recent_leads(limit: int = 10) -> pd.DataFrame:
    """Retourne les N derniers contacts ajoutés avec colonnes essentielles."""
    df = get_all_leads_df()
    if df.empty:
        return df

    cols = ["first_name", "last_name", "job_title", "company", "proposed_email", "confidence_score", "status", "profile_url"]
    present_cols = [c for c in cols if c in df.columns]
    return df[present_cols].head(limit)


def delete_leads(lead_ids: List[int]) -> bool:
    """Supprime une liste de leads par leurs identifiants."""
    if not lead_ids:
        return True
    try:
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in lead_ids)
            cursor.execute(f"DELETE FROM leads WHERE id IN ({placeholders})", lead_ids)
            conn.commit()
            return True
    except Exception:
        return False


def clean_and_deduplicate_database() -> int:
    """Nettoie la base de données de tous les doublons résiduels et régénère l'Excel."""
    try:
        from storage.exporter import excel_exporter
        if hasattr(db_manager, "deduplicate_and_clean_db"):
            deleted_count = db_manager.deduplicate_and_clean_db()
        else:
            with db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM leads
                    WHERE id NOT IN (
                        SELECT MAX(id)
                        FROM leads
                        GROUP BY LOWER(first_name), LOWER(last_name), LOWER(company)
                    );
                """)
                deleted_count = cursor.rowcount
                conn.commit()

        # Régénération immédiate du fichier Excel propre
        excel_exporter.export_from_db()
        return deleted_count
    except Exception as e:
        print(f"Erreur nettoyage base: {e}")
        return 0


def deep_verify_all_leads_process() -> Dict[str, int]:
    """Exécute l'audit complet personne par personne et email par email, et régénère l'Excel."""
    try:
        from storage.exporter import excel_exporter
        if hasattr(db_manager, "deep_verify_and_clean_db"):
            stats = db_manager.deep_verify_and_clean_db()
        else:
            cleaned = clean_and_deduplicate_database()
            stats = {"total": 0, "deleted_or_duplicates": cleaned, "verified": 0}

        # Régénération immédiate du fichier Excel propre et de l'archive horodatée
        excel_exporter.export_from_db()
        return stats
    except Exception as e:
        print(f"Erreur vérification profonde : {e}")
        return {"total": 0, "deleted_or_duplicates": 0, "verified": 0}
