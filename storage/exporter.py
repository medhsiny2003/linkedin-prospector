import os
import csv
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

class Exporter:
    """Handles exporting deduplicated prospects data to Excel, CSV, and JSON."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _generate_filename(self, extension: str) -> str:
        """Generates an automated timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        return os.path.join(self.output_dir, f"prospects_{timestamp}.{extension}")

    def deduplicate_prospects(self, prospects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates prospects by (first_name, last_name, company).
        Keeps only the record with the highest confidence score.
        Merges alternative emails into email_alt1 / email_alt2 without creating duplicate rows.
        """
        dedup_map: Dict[tuple, Dict[str, Any]] = {}

        for p in prospects:
            fn = str(p.get('first_name', '')).strip().lower()
            ln = str(p.get('last_name', '')).strip().lower()
            comp = str(p.get('company', '')).strip().lower()

            key = (fn, ln, comp)
            score = int(p.get('confidence_score') or 0)

            if key not in dedup_map:
                dedup_map[key] = dict(p)
            else:
                existing = dedup_map[key]
                existing_score = int(existing.get('confidence_score') or 0)

                # Keep higher score as primary email
                if score > existing_score:
                    # Previous email becomes alternative
                    if existing.get('email') and existing.get('email') != p.get('email'):
                        p['email_alt1'] = existing.get('email')
                    dedup_map[key] = dict(p)
                else:
                    # Current email becomes alternative if different
                    if p.get('email') and p.get('email') != existing.get('email'):
                        existing['email_alt1'] = p.get('email')

        return list(dedup_map.values())

    def export_excel(self, prospects: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
        """
        Exports deduplicated prospects to a professional multi-tab Excel workbook.
        Sheet 1: Résumé & KPIs
        Sheet 2: Prospects LinkedIn (No duplicates, highest score kept, alternative email column)
        """
        deduped = self.deduplicate_prospects(prospects)
        filepath = output_path or self._generate_filename("xlsx")

        wb = Workbook()

        # --- Sheet 1: KPIs ---
        ws_kpi = wb.active
        ws_kpi.title = "Résumé & KPIs"

        total_contacts = len(deduped)
        validated = sum(1 for p in deduped if str(p.get('mx_status', '')).lower() == 'valid')
        validation_rate = (validated / total_contacts * 100) if total_contacts > 0 else 0
        scores = [int(p.get('confidence_score') or 0) for p in deduped if p.get('confidence_score')]
        avg_score = (sum(scores) / len(scores)) if scores else 0

        companies = {}
        for p in deduped:
            c = p.get('company', 'Inconnu')
            companies[c] = companies.get(c, 0) + 1

        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        title_font = Font(size=14, bold=True, color="1F4E79")
        bold_font = Font(bold=True)

        ws_kpi.cell(row=2, column=2, value="LinkedIn Prospector V3.2 — Tableau de Bord d'Extraction").font = title_font
        ws_kpi.cell(row=4, column=2, value="Total Contacts Uniques :").font = bold_font
        ws_kpi.cell(row=4, column=3, value=total_contacts)
        ws_kpi.cell(row=5, column=2, value="Taux de Validation MX :").font = bold_font
        ws_kpi.cell(row=5, column=3, value=f"{validation_rate:.1f}%")
        ws_kpi.cell(row=6, column=2, value="Score Moyen de Confiance :").font = bold_font
        ws_kpi.cell(row=6, column=3, value=f"{avg_score:.1f}%")

        ws_kpi.cell(row=8, column=2, value="Répartition par Entreprise").font = Font(bold=True, size=12, color="1F4E79")
        ws_kpi.cell(row=9, column=2, value="Entreprise").font = header_font
        ws_kpi.cell(row=9, column=2).fill = header_fill
        ws_kpi.cell(row=9, column=3, value="Nombre de Profils").font = header_font
        ws_kpi.cell(row=9, column=3).fill = header_fill

        curr_row = 10
        for comp, cnt in sorted(companies.items(), key=lambda x: x[1], reverse=True):
            ws_kpi.cell(row=curr_row, column=2, value=comp)
            ws_kpi.cell(row=curr_row, column=3, value=cnt)
            curr_row += 1

        ws_kpi.column_dimensions['B'].width = 35
        ws_kpi.column_dimensions['C'].width = 25

        # --- Sheet 2: Prospects LinkedIn ---
        ws_data = wb.create_sheet(title="Prospects LinkedIn")

        headers = [
            "ID", "Prénom", "Nom", "Poste", "Entreprise",
            "Email Principal", "Score (%)", "Statut MX", "Email Alternatif",
            "URL LinkedIn", "Date d'Extraction"
        ]

        for col_idx, h in enumerate(headers, 1):
            cell = ws_data.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws_data.freeze_panes = "A2"
        ws_data.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(deduped) + 1}"

        green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        yellow_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

        for row_idx, p in enumerate(deduped, 2):
            score_val = int(p.get('confidence_score') or 0)
            alt_emails = p.get('email_alt1') or p.get('email_alt2') or ''

            ws_data.cell(row=row_idx, column=1, value=p.get('id', row_idx - 1))
            ws_data.cell(row=row_idx, column=2, value=p.get('first_name', ''))
            ws_data.cell(row=row_idx, column=3, value=p.get('last_name', ''))
            ws_data.cell(row=row_idx, column=4, value=p.get('title', ''))
            ws_data.cell(row=row_idx, column=5, value=p.get('company', ''))
            ws_data.cell(row=row_idx, column=6, value=p.get('email', ''))

            score_cell = ws_data.cell(row=row_idx, column=7, value=score_val)
            if score_val >= 80:
                score_cell.fill = green_fill
            elif score_val >= 50:
                score_cell.fill = yellow_fill
            else:
                score_cell.fill = red_fill

            ws_data.cell(row=row_idx, column=8, value=p.get('mx_status', ''))
            ws_data.cell(row=row_idx, column=9, value=alt_emails)
            ws_data.cell(row=row_idx, column=10, value=p.get('linkedin_url', ''))
            ws_data.cell(row=row_idx, column=11, value=str(p.get('extraction_date', '')))

        # Adjust column widths
        for col in ws_data.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            ws_data.column_dimensions[col_letter].width = max(max_len + 3, 12)

        wb.save(filepath)
        logger.info(f"Export Excel dédoublonné sauvegardé dans {filepath} ({total_contacts} profils uniques)")
        return filepath

    def export(self, prospects: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
        """Compatibility alias for export_excel."""
        return self.export_excel(prospects, output_path=output_path)

    def export_csv(self, prospects: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
        """Exports deduplicated prospects to a CSV file."""
        deduped = self.deduplicate_prospects(prospects)
        filepath = output_path or self._generate_filename("csv")
        if not deduped:
            return filepath

        keys = ["id", "first_name", "last_name", "title", "company", "email", "confidence_score", "mx_status", "email_alt1", "linkedin_url", "extraction_date"]
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(deduped)

        return filepath

    def export_json(self, prospects: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
        """Exports deduplicated prospects to JSON."""
        deduped = self.deduplicate_prospects(prospects)
        filepath = output_path or self._generate_filename("json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(deduped, f, indent=2, ensure_ascii=False)
        return filepath

ExcelExporter = Exporter
