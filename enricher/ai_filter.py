"""
Module de filtrage intelligent des profils par IA (Gemini 1.5 Flash / Fallback sémantique local).
Analyse la pertinence contextuelle, gère les synonymes multilingues (FR/EN)
et attribue un score de 0 à 10 avec explication concise.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
import httpx
from config import config
from core.monitoring.audit_logger import audit_logger


class AIFilter:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY") or getattr(config, "GOOGLE_API_KEY", "")
        self.model_name = "gemini-3.6-flash"
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        self.timeout = 18.0

    def is_configured(self) -> bool:
        """Indique si une clé API Google Gemini est activement renseignée."""
        return bool(self.api_key and self.api_key.strip() and not self.api_key.startswith("your_"))

    def filter_profiles_batch(
        self,
        profiles: List[Dict[str, Any]],
        target_keywords: List[str],
        target_location: str = "",
        min_score: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Filtre une liste de profils extraits par rapport aux critères de recherche et à la zone géographique.
        Utilise Gemini Flash par lot si configuré, sinon bascule sur le fallback sémantique local.
        """
        if not profiles:
            return []

        if not target_keywords and not target_location:
            return profiles

        # 1. Utilisation de l'IA Gemini si disponible
        if self.is_configured():
            try:
                ai_results = self._call_gemini_batch(profiles, target_keywords, target_location)
                if ai_results:
                    filtered = []
                    for idx, profile in enumerate(profiles):
                        res = ai_results.get(idx, {})
                        score = res.get("score", 5)
                        reason = res.get("reason", "Qualifié par IA")
                        is_relevant = res.get("relevant", True)

                        if is_relevant and score >= min_score:
                            p_copy = dict(profile)
                            p_copy["ai_score"] = score
                            p_copy["ai_reason"] = reason
                            filtered.append(p_copy)
                    
                    audit_logger.log_event(
                        "AI_FILTER_SUCCESS",
                        f"Filtrage IA Gemini : {len(filtered)}/{len(profiles)} profils retenus",
                        {"keywords": target_keywords, "location": target_location}
                    )
                    return filtered
            except Exception as e:
                audit_logger.log_event("AI_FILTER_WARN", f"Erreur Gemini, basculement sur fallback local : {e}")

        # 2. Fallback sémantique local (tolérance aux synonymes et équivalences métier)
        return self._local_semantic_fallback(profiles, target_keywords, target_location, min_score)

    def _call_gemini_batch(
        self,
        profiles: List[Dict[str, Any]],
        target_keywords: List[str],
        target_location: str = ""
    ) -> Dict[int, Dict[str, Any]]:
        """Envoie un lot de profils à Gemini Flash et récupère une structure JSON."""
        profiles_payload = []
        for idx, p in enumerate(profiles):
            profiles_payload.append({
                "id": idx,
                "name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                "title": p.get("job_title", "") or p.get("title", ""),
                "company": p.get("company", ""),
                "location": p.get("location", "")
            })

        keywords_str = ", ".join(target_keywords)
        loc_str = target_location or "Non spécifiée"

        prompt = f"""Tu es un expert senior en recrutement technique, détection de talents d'ingénierie et prospection B2B de pointe.
Analyse la liste de profils ci-dessous et évalue leur pertinence pour ces critères de recherche :
CRITÈRES DE RECHERCHE : Mots-clés/Postes ciblés = [{keywords_str}], Zone géographique requise = [{loc_str}]

CONNAISSANCES TECHNIQUES & ACRONYMES À RECONNAÎTRE :
- AÉRONAUTIQUE, DRONES & GUIDAGE : GNC (Guidance, Navigation and Control / Guidage Navigation Commande), UAV, UAS, Drones, Pilote de drone, Systèmes autonomes, Avionique, Aérostructures, Propulsion, Mécatronique, Vol, Aérodynamique.
- ÉLECTROTECHNIQUE & ÉNERGIE : Électrotechnique, Électrique, Électronique de puissance, Haute Tension (HTA/HTB), Basse Tension (BT), Variateurs de vitesse, Schémas électriques, EPLAN, Câblage, Réseaux électriques, Postes sources, Transformateurs, Courants forts/faibles.
- SYSTÈMES EMBARQUÉS & ÉLECTRONIQUE : Firmware, C/C++, RTOS, Linux embarqué, Microcontrôleurs, STM32, Arduino, ESP32, FPGA, VHDL, DSP, CAN, LIN, Bus de communication, PCB, Altium, Hardware, Électronique analogique/numérique.
- AUTOMATISME & ROBOTIQUE : Automates (PLC, API), SCADA, Supervision, Siemens (TIA Portal, S7), Schneider, Rockwell, Robotique industrielle, ROS, Motion Control, Vision industrielle, Régulation, Instrumentation, Capteurs.
- MAINTENANCE & INDUSTRIE : GMAO (Gestion de Maintenance Assistée par Ordinateur), Fiabilité, Méthodes, Maintenance préventive/curative, Électromécanique, Climatisation industrielle, CVC / HVAC, Facilities Management, Utilités industrielles, Lean, Amélioration continue.
- BUREAU D'ÉTUDES & CONCEPTION : BE (Bureau d'Études), Ingénieur R&D, Conception mécanique, CAO/DAO, CATIA, SolidWorks, AutoCAD, ANSYS, Modélisation, Calcul de structures.
- DÉCIDEURS & RH : DRH, RH, Recruteurs, Talent Acquisition, Directeurs de Site/Usine, Directeurs Techniques (CTO), Chefs de Projets, Responsables BE, Responsables Maintenance, Ingénieurs d'Affaires.

DIRECTIVES D'ÉVALUATION (HAUT RENDEMENT & COUVERTURE TOTALE) :
1. RESPECT DE LA ZONE GÉOGRAPHIQUE : Si la zone demandée est '{loc_str}', rejette uniquement les profils expressément situés dans un pays étranger sans lien avec cette zone. Si le profil est dans la zone ou non précisé, conserve-le.
2. DISSOCIATION NOM DE PERSONNE VS ENTREPRISE : Attention aux homonymies ! Si une personne porte un nom de famille ou prénom qui ressemble à une entreprise (ex: personne nommée 'Saber' alors que l'entreprise cible est 'Seaber', ou personne travaillant chez 'OCP' alors que la cible est 'Seaber'), REJETTE ce profil (relevant=false, score=1). La personne doit travailler pour l'entreprise ciblée.
3. COMPRÉHENSION SÉMANTIQUE LARGE : TOUS les profils d'Ingénieurs, Techniciens, Chefs de projet, Développeurs, Automaticiens, Électrotechniciens, Spécialistes GNC/Drones, Responsables maintenance et Équipes techniques de l'entreprise cible sont PERTINENTS (relevant=true, score entre 6 et 10).
4. DÉCIDEURS : Les profils RH, DRH, Recruteurs et Directeurs sont TOUJOURS QUALIFIÉS (relevant=true, score entre 7 et 10).
5. FORMAT : Réponds UNIQUEMENT avec un tableau JSON valide au format exact :
[
  {{"id": 0, "relevant": true, "score": 9, "reason": "Expert GNC / Systèmes autonomes au Maroc"}},
  {{"id": 1, "relevant": true, "score": 8, "reason": "Ingénieur Maintenance & GMAO"}}
]

PROFILS À ANALYSER :
{json.dumps(profiles_payload, ensure_ascii=False)}
"""

        req_body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.95,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json"
            }
        }

        url = f"{self.api_url}?key={self.api_key.strip()}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=req_body)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:100]}")

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return {}

            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            if match:
                items = json.loads(match.group(0))
                return {item["id"]: item for item in items if "id" in item}

        return {}

    @staticmethod
    def strip_accents(text: str) -> str:
        """Supprime les accents (ex: 'électrotechnique' -> 'electrotechnique')."""
        import unicodedata
        return "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))

    def _local_semantic_fallback(
        self,
        profiles: List[Dict[str, Any]],
        target_keywords: List[str],
        target_location: str = "",
        min_score: int = 3
    ) -> List[Dict[str, Any]]:
        """Fallback sémantique local enrichi avec dictionnaire exhaustif de sigles et acronymes d'ingénierie."""
        synonyms = {
            "gnc": ["gnc", "guidance", "navigation", "control", "guidag", "commande", "automatiq", "asserviss", "aero", "drone", "uav", "uas", "avioniqu", "pilote", "vol"],
            "drone": ["uav", "uas", "drone", "gnc", "embarqu", "aero", "robot", "autonom", "system", "avioniqu", "propulsion", "vol", "aerodynamiq", "aeronaval"],
            "electrotechnique": ["electri", "electron", "puissance", "energie", "power", "hardware", "cablage", "maintenance", "eplan", "variateur", "transformateur", "hta", "htb", "bt", "schematiq", "armoire"],
            "robotique": ["robot", "automat", "ros", "motion", "controle", "vision", "mecatronique", "cobot", "plc", "scada", "automatisme", "capteur"],
            "embarque": ["embedded", "firmware", "c++", "c/c++", "rtos", "linux", "stm32", "microcontrol", "fpga", "vhdl", "dsp", "can", "bsp", "arduino", "esp32"],
            "maintenance": ["maintenance", "gmao", "fiabilit", "methode", "instrumentation", "electromecanic", "technicien", "technique", "travaux", "installation", "depannage", "facility", "facilities", "cvc", "hvac", "utilite"],
            "automatisme": ["automat", "plc", "scada", "siemens", "schneider", "tia portal", "regulat", "supervision", "automatisme", "api", "rockwell"],
            "be": ["bureau d'etude", "conception", "cao", "dao", "catia", "solidworks", "ansys", "autocad", "r&d", "calcul", "structure", "mecanique"],
            "rh": ["recrut", "talent", "hr", "ressources humaines", "people", "staffing", "acquisition", "drh", "charge de recrut", "headhunter"],
            "direction": ["directeur", "responsable", "manager", "lead", "head", "chef de projet", "charge d'affaires", "cto", "coo", "vp", "site manager"]
        }

        kw_tokens = []
        for kw in target_keywords:
            kw_no_acc = self.strip_accents(kw.lower())
            clean_kw = re.sub(r'[^a-z0-9]', '', kw_no_acc)
            kw_tokens.append(clean_kw)
            for k, syn_list in synonyms.items():
                if k in clean_kw or clean_kw in k:
                    kw_tokens.extend(syn_list)

        loc_clean = target_location.strip().lower()

        filtered = []
        for p in profiles:
            raw_title = (p.get("job_title") or p.get("title") or "").lower()
            title = self.strip_accents(raw_title)
            p_loc = (p.get("location") or "").lower()
            p_full = f"{title} {p_loc}"

            # Contrôle de localisation géographique strict
            if "maroc" in loc_clean:
                has_maroc = any(city in p_full for city in ["maroc", "morocco", "casablanca", "rabat", "tanger", "kenitra", "marrakech", "benguerir", "agadir", "fès", "fes", "oujda", "salé", "el jadida", "tétouan"])
                has_france_only = any(city in p_full for city in ["région de paris", "lyon, france", "paris, france", "toulouse, france", "bordeaux, france", "nantes, france", "marseille, france", "île-de-france", "ile-de-france"])
                if has_france_only and not has_maroc:
                    continue
            elif "france" in loc_clean:
                has_france = any(city in p_full for city in ["france", "paris", "lyon", "toulouse", "bordeaux", "nantes", "marseille", "lille", "strasbourg", "rennes"])
                has_foreign_only = any(city in p_full for city in ["casablanca", "rabat", "tanger", "maroc", "morocco", "algerie", "tunisie"])
                if has_foreign_only and not has_france:
                    continue

            if not title:
                filtered.append(p)
                continue

            # Détection des métiers totalement hors-sujet
            unrelated = ["securite", "securitaire", "gardien", "caissier", "chauffeur", "plombier", "infirmier", "magasinier", "nettoyage"]
            if any(u in title for u in unrelated):
                continue  # Éliminé d'office

            score = 2
            reason = "Correspondance standard"

            # Bonus décideur / RH / Direction
            if any(term in title for term in ["recrut", "talent", "rh", "drh", "directeur", "lead", "manager", "responsable", "chef"]):
                score += 5
                reason = "Décideur / Profil RH ciblé"

            # Bonus mots-clés & sigles techniques (GNC, GMAO, PLC...)
            matches = [token for token in kw_tokens if token in title]
            if matches:
                score += min(len(matches) * 3, 6)
                reason = f"Correspondance technique ({', '.join(matches[:2])})"

            if score >= min_score:
                p_copy = dict(p)
                p_copy["ai_score"] = min(score, 10)
                p_copy["ai_reason"] = reason
                filtered.append(p_copy)

        return filtered


ai_filter = AIFilter()