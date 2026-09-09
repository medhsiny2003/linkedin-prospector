import unicodedata
import re
from typing import List, Tuple

class EmailGenerator:
    """Generates 22 email permutations across Light, Medium, and Heavy tiers with confidence scores."""

    PATTERNS = {
        'light': [
            ('{first}.{last}@{domain}', 95),
            ('{first}{last}@{domain}', 90),
            ('{f}.{last}@{domain}', 85),
            ('{first}.{l}@{domain}', 80),
        ],
        'medium': [
            ('{first}.{last}@{domain}', 95),
            ('{first}{last}@{domain}', 90),
            ('{f}.{last}@{domain}', 85),
            ('{first}.{l}@{domain}', 80),
            ('{last}.{first}@{domain}', 70),
            ('{first}_{last}@{domain}', 68),
            ('{first}-{last}@{domain}', 65),
            ('{f}{last}@{domain}', 63),
            ('{first}{l}@{domain}', 60),
            ('{last}{f}@{domain}', 58),
            ('{l}.{first}@{domain}', 55),
        ],
        'heavy': [
            ('{first}.{last}@{domain}', 95),
            ('{first}{last}@{domain}', 90),
            ('{f}.{last}@{domain}', 85),
            ('{first}.{l}@{domain}', 80),
            ('{last}.{first}@{domain}', 70),
            ('{first}_{last}@{domain}', 68),
            ('{first}-{last}@{domain}', 65),
            ('{f}{last}@{domain}', 63),
            ('{first}{l}@{domain}', 60),
            ('{last}{f}@{domain}', 58),
            ('{l}.{first}@{domain}', 55),
            ('{first}@{domain}', 40),
            ('{last}@{domain}', 38),
            ('{l}{first}@{domain}', 35),
            ('{last}_{f}@{domain}', 33),
            ('{first}.{last}1@{domain}', 30),
            ('{first}{last}1@{domain}', 28),
            ('{first}.{last}.pro@{domain}', 25),
            ('{f}_{last}@{domain}', 23),
            ('{f}-{last}@{domain}', 22),
            ('{first}{last}01@{domain}', 21),
            ('{last}.{f}@{domain}', 20),
        ]
    }

    def _normalize_name(self, name: str) -> str:
        """Removes accents, lowercase, and non-alphanumeric characters."""
        if not name:
            return ""
        name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
        name = name.lower().strip()
        name = name.replace('-', '').replace(' ', '')
        name = re.sub(r'[^a-z0-9]', '', name)
        return name

    def generate(self, first_name: str, last_name: str, domain: str, level: str = 'medium') -> List[Tuple[str, int]]:
        """Generates sorted email permutations with confidence scores."""
        norm_first = self._normalize_name(first_name)
        norm_last = self._normalize_name(last_name)
        domain = domain.lower().strip()
        
        if not norm_first or not norm_last or not domain:
            return []

        f = norm_first[0] if norm_first else ""
        l = norm_last[0] if norm_last else ""
        
        patterns = self.PATTERNS.get(level, self.PATTERNS['medium'])
        
        emails = []
        seen = set()
        for template, score in patterns:
            email = template.format(first=norm_first, last=norm_last, f=f, l=l, domain=domain)
            if email not in seen:
                emails.append((email, score))
                seen.add(email)
                
        return sorted(emails, key=lambda x: x[1], reverse=True)

    def get_best_email(self, first_name: str, last_name: str, domain: str, level: str = 'medium') -> Tuple[str, int]:
        """Returns the highest scored email candidate."""
        emails = self.generate(first_name, last_name, domain, level)
        return emails[0] if emails else ("", 0)

    def get_top_n_emails(self, first_name: str, last_name: str, domain: str, n: int = 3, level: str = 'medium') -> List[Tuple[str, int]]:
        """Returns the top N candidates by confidence score."""
        emails = self.generate(first_name, last_name, domain, level)
        return emails[:n]
