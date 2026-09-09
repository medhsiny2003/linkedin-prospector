import os
import csv
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

class Exporter:
    """Handles exporting prospects data to Excel, CSV, and JSON."""

    def __init__(self, output_dir: str = "d:/PROJECT hsiny/DATA/linkedin-prospector/output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _generate_filename(self, extension: str) -> str:
        """Generates an automated timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        return os.path.join(self.output_dir, f"prospects_{timestamp}.{extension}")

    def export_excel(self, prospects: List[Dict[str, Any]]) -> str:
        """
        Exports prospects to a professional multi-tab Excel workbook.
        Sheet 1: Résumé & KPIs
        Sheet 2: Prospects LinkedIn
        """
        wb = Workbook()
        
        # Setup Sheet 1: KPIs
        ws_kpi = wb.active
        ws_kpi.title = "Résumé & KPIs"
        
        # Calculate KPIs
        total_contacts = len(prospects)
        validated = sum(1 for p in prospects if p.get('mx_status') == 'valid')
        validation_rate = (validated / total_contacts * 100) if total_contacts > 0 else 0
        
        scores = [p.get('confidence_score', 0) for p in prospects if isinstance(p.get('confidence_score'), (int, float))]
        avg_score = (sum(scores) / len(scores)) if scores else 0
        
        companies = {}
        for p in prospects:
            c = p.get('company', 'Unknown')
            companies[c] = companies.get(c, 0) + 1
            
        # Write KPIs
        ws_kpi.append(["Key Performance Indicators"])
        ws_kpi.append(["Total Contacts", total_contacts])
        ws_kpi.append(["Validated Contacts", validated])
        ws_kpi.append(["Validation Rate", f"{validation_rate:.2f}%"])
        ws_kpi.append(["Average Confidence Score", f"{avg_score:.2f}"])
        ws_kpi.append([])
        ws_kpi.append(["Breakdown by Company"])
        ws_kpi.append(["Company", "Count"])
        for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True):
            ws_kpi.append([company, count])
            
        # Format KPI Sheet
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        
        for cell in ws_kpi[1]:
            cell.font = header_font
            cell.fill = header_fill
            
        ws_kpi['A7'].font = header_font
        ws_kpi['A7'].fill = header_fill
        ws_kpi['B7'].font = header_font
        ws_kpi['B7'].fill = header_fill

        ws_kpi.column_dimensions['A'].width = 30
        ws_kpi.column_dimensions['B'].width = 15

        # Setup Sheet 2: Prospects
        ws_prospects = wb.create_sheet(title="Prospects LinkedIn")
        
        headers = [
            "ID", "Name", "Title", "Company", "Location", "LinkedIn URL",
            "Email", "MX Status", "Confidence Score", "Keyword", "Extraction Date"
        ]
        
        ws_prospects.append(headers)
        
        # Format Headers
        for col_idx, header in enumerate(headers, 1):
            cell = ws_prospects.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
        ws_prospects.freeze_panes = "A2"
        ws_prospects.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(prospects) + 1}"
        
        # Add Data and Conditional Formatting
        green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        yellow_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

        for row_idx, p in enumerate(prospects, 2):
            score = p.get('confidence_score', 0)
            row_data = [
                p.get('id', ''),
                p.get('name', ''),
                p.get('title', ''),
                p.get('company', ''),
                p.get('location', ''),
                p.get('linkedin_url', ''),
                p.get('email', ''),
                p.get('mx_status', ''),
                score,
                p.get('keyword', ''),
                p.get('extraction_date', '')
            ]
            
            for col_idx, val in enumerate(row_data, 1):
                cell = ws_prospects.cell(row=row_idx, column=col_idx, value=val)
                
                # Conditional score colors
                if col_idx == 9:  # Confidence Score column
                    try:
                        score_val = int(score) if score else 0
                        if score_val >= 80:
                            cell.fill = green_fill
                        elif score_val >= 50:
                            cell.fill = yellow_fill
                        else:
                            cell.fill = red_fill
                    except ValueError:
                        pass
                        
        # Adjust column widths
        for col in ws_prospects.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws_prospects.column_dimensions[col_letter].width = adjusted_width

        filepath = self._generate_filename("xlsx")
        wb.save(filepath)
        logger.info(f"Excel export saved to {filepath}")
        return filepath

    def export_csv(self, prospects: List[Dict[str, Any]]) -> str:
        """Exports prospects to a CSV file."""
        filepath = self._generate_filename("csv")
        if not prospects:
            logger.warning("No prospects to export to CSV.")
            return filepath
            
        keys = prospects[0].keys() if prospects else []
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(prospects)
            
        logger.info(f"CSV export saved to {filepath}")
        return filepath

    def export_json(self, prospects: List[Dict[str, Any]]) -> str:
        """Exports prospects to a JSON file."""
        filepath = self._generate_filename("json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(prospects, f, indent=4, ensure_ascii=False)
            
        logger.info(f"JSON export saved to {filepath}")
        return filepath

    def export(self, prospects: List[Dict[str, Any]], output_path: str = None) -> str:
        """Alias for export_excel for backwards compatibility."""
        if output_path:
            # Custom path
            wb = Workbook()
            ws_kpi = wb.active
            ws_kpi.title = "Résumé & KPIs"
            total_contacts = len(prospects)
            validated = sum(1 for p in prospects if p.get('mx_status') == 'valid')
            validation_rate = (validated / total_contacts * 100) if total_contacts > 0 else 0
            valid_scores = [p.get('confidence_score', 0) for p in prospects if p.get('confidence_score')]
            avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

            ws_kpi.cell(row=2, column=2, value="LinkedIn Prospector V3.2 - Résumé d'Extraction").font = Font(size=14, bold=True, color="1F4E79")
            ws_kpi.cell(row=4, column=2, value="Total Contacts :").font = Font(bold=True)
            ws_kpi.cell(row=4, column=3, value=total_contacts)
            ws_kpi.cell(row=5, column=2, value="Taux de Validation MX :").font = Font(bold=True)
            ws_kpi.cell(row=5, column=3, value=f"{validation_rate:.1f}%")
            ws_kpi.cell(row=6, column=2, value="Score Moyen :").font = Font(bold=True)
            ws_kpi.cell(row=6, column=3, value=f"{avg_score:.1f}%")

            ws_data = wb.create_sheet(title="Prospects LinkedIn")
            headers = ["ID", "Prénom", "Nom", "Poste", "Entreprise", "Email Proposé", "Score (%)", "Statut MX", "Serveur MX", "URL LinkedIn", "Date"]
            header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)
            for col_idx, h in enumerate(headers, 1):
                cell = ws_data.cell(row=1, column=col_idx, value=h)
                cell.fill = header_fill
                cell.font = header_font

            for row_idx, p in enumerate(prospects, 2):
                ws_data.cell(row=row_idx, column=1, value=p.get('id', ''))
                ws_data.cell(row=row_idx, column=2, value=p.get('first_name', ''))
                ws_data.cell(row=row_idx, column=3, value=p.get('last_name', ''))
                ws_data.cell(row=row_idx, column=4, value=p.get('title', ''))
                ws_data.cell(row=row_idx, column=5, value=p.get('company', ''))
                ws_data.cell(row=row_idx, column=6, value=p.get('email', ''))
                ws_data.cell(row=row_idx, column=7, value=p.get('confidence_score', 0))
                ws_data.cell(row=row_idx, column=8, value=p.get('mx_status', ''))
                ws_data.cell(row=row_idx, column=9, value=p.get('mx_active', ''))
                ws_data.cell(row=row_idx, column=10, value=p.get('linkedin_url', ''))
                ws_data.cell(row=row_idx, column=11, value=str(p.get('extraction_date', '')))

            wb.save(output_path)
            return output_path
        return self.export_excel(prospects)

# Alias for backwards compatibility
ExcelExporter = Exporter

