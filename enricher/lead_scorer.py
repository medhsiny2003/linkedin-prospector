"""
Moteur de scoring intelligent et de priorisation des leads pour stages.
Évalue la pertinence d'un contact en fonction de son poste (RH / Drones / Embarqué),
de la validité de son email et de la confiance du pattern.
"""

import re
from typing import Dict, Tuple


class LeadScorer:
    def __init__(self):
        # Mots-clés de haute priorité pour un stage en drones / électronique / robotique
        self.hr_keywords = [
            "rh", "ressources humaines", "recruteur", "recruteuse", "recrutement",
            "talent acquisition", "chargé de recrutement", "campus manager",
            "relations écoles", "hr", "talent", "headhunter", "people"
        ]
        self.tech_keywords = [
            "r&d", "robotique", "systèmes embarqués", "embedded", "drone", "uav",
            "chef de projet", "lead", "directeur technique", "cto", "responsable",
            "ingénieur", "hardware", "software", "électronique", "automatisme"
        ]

    def calculate_score(self, lead: Dict[str, any]) -> Tuple[int, str, str]:
        """
        Calcule un score de 0 à 100, une évaluation en étoiles (★★★) et un badge.
        Retourne (score, etoiles, badge_recommandation).
        """
        score = 0
        job_title = str(lead.get("job_title", "")).lower()
        mx_status = str(lead.get("mx_verified", "")).lower()
        confidence = int(lead.get("confidence_score", 0) or 0)

        # 1. Pertinence du poste (jusqu'à 50 points)
        if any(re.search(r'\b' + re.escape(kw) + r'\b', job_title) for kw in self.hr_keywords):
            score += 50  # Décideur Recrutement / RH (Idéal pour postuler)
        elif any(re.search(r'\b' + re.escape(kw) + r'\b', job_title) for kw in self.tech_keywords):
            score += 40  # Responsable Technique / Drone / Embarqué (Idéal pour candidature spontanée)
        else:
            score += 15  # Autre collaborateur

        # 2. Qualité et validation de l'adresse email (jusqu'à 30 points)
        status_str = str(lead.get("status", ""))
        if "Validé (SMTP" in status_str or "Validé (MX Direct)" in status_str:
            score += 30
        elif "Validé (Catch-All)" in status_str or "Catch-All" in status_str:
            score += 22  # Domaine Catch-All : bonne probabilité mais non garantie à 100%
        elif mx_status in ["oui", "yes", "validé", "valide"]:
            score += 25
        elif "À vérifier" in status_str:
            score += 10

        # 3. Confiance du pattern déterministe (jusqu'à 20 points)
        if confidence >= 85:
            score += 20
        elif confidence >= 60:
            score += 10
        else:
            score += 5

        # 4. Ajustement par le score sémantique IA si présent
        ai_score = lead.get("ai_score")
        if ai_score is not None:
            score = int((score * 0.85) + (int(ai_score) * 1.5))

        # Plafonnement entre 0 et 100
        score = min(max(score, 0), 100)

        # Attribution des étoiles et recommandations
        if score >= 80:
            stars = "★★★"
            badge = "Priorité Haute (Candidature recommandée)"
        elif score >= 55:
            stars = "★★☆"
            badge = "Priorité Moyenne (Contact pertinent)"
        else:
            stars = "★☆☆"
            badge = "Priorité Standard"

        return score, stars, badge


lead_scorer = LeadScorer()
