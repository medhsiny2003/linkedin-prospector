from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Contact:
    first_name: str = ''
    last_name: str = ''
    title: str = ''
    company: str = ''
    linkedin_url: str = ''
    email: str = ''
    email_alt1: str = ''
    email_alt2: str = ''
    confidence_score: int = 0
    mx_status: str = 'unknown'  # valid, invalid, unknown, catch-all
    mx_active: bool = False
    extraction_date: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = 'xray'  # xray or stealth
