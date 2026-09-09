import json
import os
from typing import Dict, List, Optional
from .email_generator import EmailGenerator

class PatternDetector:
    def __init__(self):
        self._cache: Dict[str, str] = {}
        self.generator = EmailGenerator()

    def detect_pattern(self, domain: str, known_emails: Optional[List[Dict]] = None) -> Optional[str]:
        if domain in self._cache:
            return self._cache[domain]
            
        if not known_emails:
            return None
            
        pattern_counts = {}
        for entry in known_emails:
            email = entry.get('email')
            first = entry.get('first_name', '')
            last = entry.get('last_name', '')
            if not email or not first or not last:
                continue
                
            matched_pattern = self._match_pattern(email, first, last, domain)
            if matched_pattern:
                pattern_counts[matched_pattern] = pattern_counts.get(matched_pattern, 0) + 1
                
        if pattern_counts:
            best_pattern = max(pattern_counts.items(), key=lambda x: x[1])[0]
            self._cache[domain] = best_pattern
            return best_pattern
            
        return None

    def _match_pattern(self, email: str, first_name: str, last_name: str, domain: str) -> Optional[str]:
        norm_first = self.generator._normalize_name(first_name)
        norm_last = self.generator._normalize_name(last_name)
        if not norm_first or not norm_last:
            return None
            
        f = norm_first[0]
        l = norm_last[0]
        
        for template, _ in self.generator.PATTERNS['heavy']:
            expected_email = template.format(first=norm_first, last=norm_last, f=f, l=l, domain=domain)
            if expected_email.lower() == email.lower():
                return template
        return None

    def get_cached_pattern(self, domain: str) -> Optional[str]:
        return self._cache.get(domain)

    def save_cache(self, path: str = 'data/pattern_cache.json') -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._cache, f, indent=2)

    def load_cache(self, path: str = 'data/pattern_cache.json') -> None:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self._cache = json.load(f)
