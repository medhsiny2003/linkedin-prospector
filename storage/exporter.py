import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

class ExcelExporter:
    COLUMNS = [
        ("ID", 8),
        ("Prénom", 18),
        ("Nom", 18),
        ("Poste / Rôle", 30),
        ("Entreprise", 22),
        ("Email Proposé", 32),
        ("Score de Confiance (%)", 20),
        ("Statut MX", 14),
        ("Serveur MX Valide", 25),
        ("URL LinkedIn", 45),
        ("Date d'extraction", 22)
    ]
    
    HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    HEADER_FONT = Font(bold=True, color='FFFFFF', size=11)
    BORDER_SIDE = Side(border_style="thin", color="000000")
    BORDER = Border(left=BORDER_SIDE, right=BORDER_SIDE, top=BORDER_SIDE, bottom=BORDER_SIDE)
    
    SCORE_HIGH = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    SCORE_MED = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    SCORE_LOW = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    def export(self, contacts: List[Dict], output_path: Optional[str] = None) -> str:
        if not output_path:
            os.makedirs('output', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f'output/linkedin_prospects_{timestamp}.xlsx'

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Prospects LinkedIn"

        for col_idx, (col_name, width) in enumerate(self.COLUMNS, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.fill = self.HEADER_FILL
            cell.font = self.HEADER_FONT
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = self.BORDER
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

        for row_idx, contact in enumerate(contacts, 2):
            row_data = [
                contact.get('id', ''),
                contact.get('first_name', ''),
                contact.get('last_name', ''),
                contact.get('title', ''),
                contact.get('company', ''),
                contact.get('email', ''),
                contact.get('confidence_score', 0),
                contact.get('mx_status', ''),
                contact.get('mx_active', ''),
                contact.get('linkedin_url', ''),
                self._format_date(contact.get('extraction_date', ''))
            ]
            
            for col_idx, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = self.BORDER
                cell.alignment = Alignment(horizontal='left', vertical='center')
                
                if col_idx == 7:
                    score = int(value) if value else 0
                    if score >= 80:
                        cell.fill = self.SCORE_HIGH
                    elif score >= 50:
                        cell.fill = self.SCORE_MED
                    else:
                        cell.fill = self.SCORE_LOW

        ws.auto_filter.ref = ws.dimensions
        ws.freeze_panes = 'A2'
        
        wb.save(output_path)
        return output_path

    def export_json(self, contacts: List[Dict], output_path: Optional[str] = None) -> str:
        if not output_path:
            os.makedirs('output', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f'output/results_{timestamp}.json'
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(contacts, f, ensure_ascii=False, indent=2)
            
        return output_path

    def _format_date(self, date_str: str) -> str:
        if not date_str:
            return ""
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%d/%m/%Y %H:%M')
        except Exception:
            return date_str
