"""
Client Agent-Reach AI Skills pour le mode Cloud.
Utilise mcporter (MCP) pour accéder aux profils LinkedIn de manière structurée.
Fallback automatique sur LinkedinSpider (Yahoo/Bing HTTP) si Agent-Reach n'est pas disponible.
"""

import json
import os
import subprocess
import shutil
from typing import Any, Dict, List, Optional
from core.monitoring.audit_logger import audit_logger


class AgentReachClient:
    def __init__(self):
        self._available = None  # Cache de disponibilité

    def is_available(self) -> bool:
        """Vérifie si Agent-Reach (mcporter) est installé et accessible."""
        if self._available is not None:
            return self._available
        self._available = shutil.which("mcporter") is not None
        if not self._available:
            # Tentative alternative via agent-reach
            self._available = shutil.which("agent-reach") is not None
        audit_logger.log_event(
            "AGENT_REACH_CHECK",
            f"Agent-Reach disponible : {self._available}"
        )
        return self._available

    def search_profiles(
        self,
        company: str,
        keywords: str,
        location: str = "International",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Recherche des profils LinkedIn via Agent-Reach MCP.
        Fallback automatique sur LinkedinSpider si Agent-Reach n'est pas disponible.
        """
        if not self.is_available():
            audit_logger.log_event(
                "AGENT_REACH_FALLBACK",
                "Agent-Reach non disponible. Basculement sur LinkedinSpider (Yahoo/Bing HTTP)."
            )
            return self._fallback_spider(company, keywords, location, limit)

        profiles = []

        # 1. Recherche via mcporter linkedin.find_profile_by_name
        try:
            search_query = f"{keywords} {company}"
            cmd = [
                "mcporter", "call",
                "linkedin.find_profile_by_name",
                "--args", json.dumps({
                    "name": search_query,
                    "company": company
                })
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                if isinstance(data, dict):
                    parsed = self._parse_agent_reach_profile(data, company, keywords, location)
                    if parsed:
                        profiles.append(parsed)
                elif isinstance(data, list):
                    for item in data[:limit]:
                        parsed = self._parse_agent_reach_profile(item, company, keywords, location)
                        if parsed:
                            profiles.append(parsed)
            audit_logger.log_event(
                "AGENT_REACH_SEARCH",
                f"{len(profiles)} profils trouvés via Agent-Reach pour {company} - {keywords}"
            )
        except subprocess.TimeoutExpired:
            audit_logger.log_event("AGENT_REACH_TIMEOUT", f"Timeout Agent-Reach pour {company}")
        except Exception as e:
            audit_logger.log_event("AGENT_REACH_ERROR", f"Erreur Agent-Reach : {e}")

        # 2. Compléter avec LinkedinSpider si pas assez de résultats
        if len(profiles) < limit:
            spider_profiles = self._fallback_spider(
                company, keywords, location, limit - len(profiles)
            )
            # Éviter les doublons par URL
            existing_urls = {p["profile_url"] for p in profiles if p.get("profile_url")}
            for sp in spider_profiles:
                if sp.get("profile_url") not in existing_urls:
                    profiles.append(sp)
                    existing_urls.add(sp.get("profile_url", ""))

        return profiles[:limit]

    def get_profile(self, linkedin_url_or_username: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un profil LinkedIn complet via Agent-Reach.
        """
        if not self.is_available():
            return None

        try:
            # Extraire le username de l'URL si nécessaire
            username = linkedin_url_or_username
            if "linkedin.com/in/" in username:
                username = username.split("/in/")[-1].strip("/")

            cmd = [
                "mcporter", "call",
                "linkedin.get_person_profile",
                "--args", json.dumps({"linkedin_username": username})
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except Exception as e:
            audit_logger.log_event("AGENT_REACH_PROFILE_ERROR", f"Erreur get_profile : {e}")

        return None

    def _parse_agent_reach_profile(
        self, data: dict, company: str, keywords: str, location: str
    ) -> Optional[Dict[str, Any]]:
        """Convertit un profil Agent-Reach en format interne du projet."""
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")

        # Fallback : parser full_name si first/last non fournis
        if not first_name and not last_name and data.get("full_name"):
            parts = data["full_name"].strip().split(" ", 1)
            first_name = parts[0] if parts else ""
            last_name = parts[1] if len(parts) > 1 else ""

        if not first_name or not last_name:
            return None

        # Extraire le poste depuis experience ou headline
        job_title = data.get("headline", "")
        if not job_title and data.get("experience"):
            exp = data["experience"]
            if isinstance(exp, list) and exp:
                job_title = exp[0].get("title", "")

        # Extraire l'URL du profil
        profile_url = data.get("profile_url", "")
        if not profile_url and data.get("public_identifier"):
            profile_url = f"https://www.linkedin.com/in/{data['public_identifier']}"

        return {
            "first_name": first_name,
            "last_name": last_name,
            "job_title": job_title or keywords,
            "company": company,
            "location": data.get("location", {}).get("city", location) if isinstance(data.get("location"), dict) else str(data.get("location", location)),
            "profile_url": profile_url,
            "matched_keywords": f"{company}, {keywords} (Agent-Reach MCP)"
        }

    def _fallback_spider(
        self, company: str, keywords: str, location: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback sur LinkedinSpider (Yahoo/Bing HTTP) si Agent-Reach n'est pas disponible."""
        from scrapers.linkedin_spider import linkedin_spider
        return linkedin_spider.search_profiles(
            company, keywords, location=location, limit=limit
        )


agent_reach_client = AgentReachClient()
