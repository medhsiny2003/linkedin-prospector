import json
import os
from typing import Dict, Optional

class PatternDetector:
    """Caches and retrieves successful email patterns for domains."""
    
    def __init__(self, cache_file: str = "domain_patterns.json"):
        self.cache_file = cache_file
        self.patterns: Dict[str, str] = self._load_cache()

    def _load_cache(self) -> Dict[str, str]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_cache(self) -> None:
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_file)), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.patterns, f, indent=2)
        except OSError:
            pass

    def get_pattern(self, domain: str) -> Optional[str]:
        """Retrieves a known pattern for a given domain."""
        if not domain:
            return None
        return self.patterns.get(domain.lower().strip())

    def record_pattern(self, domain: str, pattern: str) -> None:
        """Records a successful pattern for a given domain."""
        if not domain or not pattern:
            return
        domain = domain.lower().strip()
        self.patterns[domain] = pattern
        self._save_cache()
        
    def construct_from_pattern(self, first_name: str, last_name: str, domain: str, pattern: str) -> str:
        """
        Constructs an email given a pattern string like '{first}.{last}@{domain}'
        or '{f}{last}@{domain}'.
        """
        f = first_name.lower().strip()
        l = last_name.lower().strip()
        fi = f[0] if f else ""
        li = l[0] if l else ""
        d = domain.lower().strip()
        
        # Simple string replacement
        email = pattern.replace("{first}", f)
        email = email.replace("{last}", l)
        email = email.replace("{f}", fi)
        email = email.replace("{l}", li)
        email = email.replace("{domain}", d)
        
        return email
