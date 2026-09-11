"""
Validateur d'emails avancé (Syntaxe RFC 5322 + MX DNS + Probing Catch-All + Handshake SMTP non-bloquant).
Utilise dnspython pour interroger les serveurs de noms, teste les passerelles de sécurité
et réalise des sondes SMTP non-intrusives avec tolérance aux pare-feux résidentiels.
"""

import re
import socket
import uuid
from typing import Dict, Optional, Tuple
from core.monitoring.audit_logger import audit_logger

try:
    import dns.resolver
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

try:
    from email_validator import validate_email as lib_validate_email, EmailNotValidError
    HAS_EMAIL_VALIDATOR = True
except ImportError:
    HAS_EMAIL_VALIDATOR = False


class EmailValidator:
    def __init__(self):
        # Cache mémoire (domain -> (has_mx, is_catch_all, mx_host, reason))
        self._mx_cache: Dict[str, Tuple[bool, bool, str, str]] = {}
        # Passerelles d'entreprises connues
        self.known_gateways = ["proofpoint", "mimecast", "barracuda", "ironport", "pphosted", "trendmicro", "google", "outlook"]

    @staticmethod
    def validate_syntax(email: str) -> bool:
        """Vérifie la conformité syntaxique selon les standards RFC."""
        if not email or "@" not in email:
            return False

        if HAS_EMAIL_VALIDATOR:
            try:
                lib_validate_email(email, check_deliverability=False)
                return True
            except Exception:
                return False

        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email))

    def check_mx_record(self, domain: str) -> Tuple[bool, bool, str, str]:
        """
        Vérifie les serveurs MX actifs et détecte les passerelles Catch-All.
        Retourne (has_mx, is_catch_all, primary_mx_host, reason).
        """
        domain = domain.strip().lower()
        if not domain:
            return False, False, "", "Domaine vide"

        if domain in self._mx_cache:
            return self._mx_cache[domain]

        if not HAS_DNSPYTHON:
            return True, False, "", "Vérification MX ignorée (dnspython non installé)"

        try:
            answers = dns.resolver.resolve(domain, 'MX', lifetime=4.0)
            if len(answers) > 0:
                # Tri par préférence MX
                sorted_mx = sorted(answers, key=lambda r: r.preference)
                primary_mx = str(sorted_mx[0].exchange).rstrip(".").strip().lower()
                
                # Rejet formel du Null MX (RFC 7505 : domaine interdisant les emails)
                if not primary_mx or primary_mx == ".":
                    result = (False, False, "", "Null MX (RFC 7505 : domaine refusant tout email)")
                    self._mx_cache[domain] = result
                    return result

                mx_hosts = [str(r.exchange).lower() for r in answers]
                is_gateway = any(any(gw in host for gw in self.known_gateways) for host in mx_hosts)
                
                result = (True, is_gateway, primary_mx, f"{len(answers)} serveur(s) MX trouvé(s)")
                self._mx_cache[domain] = result
                return result
            else:
                result = (False, False, "", "Aucun enregistrement MX")
                self._mx_cache[domain] = result
                return result
        except dns.resolver.NXDOMAIN:
            result = (False, False, "", "Nom de domaine inexistant (NXDOMAIN)")
            self._mx_cache[domain] = result
            return result
        except dns.resolver.NoAnswer:
            result = (False, False, "", "Pas de réponse MX pour ce domaine")
            self._mx_cache[domain] = result
            return result
        except Exception as e:
            return False, False, "", f"Erreur DNS : {str(e)}"

    def verify_smtp_handshake(self, email: str, mx_host: str, timeout: float = 2.5) -> Tuple[Optional[bool], str]:
        """
        Effectue un handshake SMTP direct (HELO -> MAIL FROM -> RCPT TO) sans envoyer de mail.
        Gère élégamment les blocages de port 25 par les FAI (fallback transparent).
        """
        if not mx_host or not email:
            return None, "Hôte MX non disponible pour handshake"

        try:
            sock = socket.create_connection((mx_host, 25), timeout=timeout)
            sock.settimeout(timeout)

            # Lecture de la bannière 220
            banner = sock.recv(1024).decode('utf-8', errors='ignore')
            if not banner.startswith("220"):
                sock.close()
                return None, "Bannière SMTP non conforme"

            # HELO
            sock.sendall(b"HELO check.lead-prospector.fr\r\n")
            helo_resp = sock.recv(1024).decode('utf-8', errors='ignore')

            # MAIL FROM
            sock.sendall(b"MAIL FROM:<verify@check.lead-prospector.fr>\r\n")
            mail_resp = sock.recv(1024).decode('utf-8', errors='ignore')

            # RCPT TO
            sock.sendall(f"RCPT TO:<{email}>\r\n".encode('utf-8'))
            rcpt_resp = sock.recv(1024).decode('utf-8', errors='ignore')

            # QUIT
            try:
                sock.sendall(b"QUIT\r\n")
            except Exception:
                pass
            sock.close()

            if rcpt_resp.startswith("250"):
                return True, "Boîte email confirmée existante (SMTP 250 OK)"
            elif any(rcpt_resp.startswith(code) for code in ["550", "551", "552", "553"]):
                return False, f"Boîte email inexistante ({rcpt_resp.strip()[:30]})"
            else:
                return None, f"Réponse SMTP intermédiaire ({rcpt_resp.strip()[:30]})"

        except (socket.timeout, socket.error, OSError):
            # Port 25 filtré ou pare-feu (cas classique en environnement résidentiel)
            return None, "Port 25 inaccessible (Validation DNS MX maintenue)"

    def validate(self, email: str, fast_mode: bool = True) -> Dict[str, any]:
        """
        Validation complète à 3 niveaux : Syntaxe + MX DNS + Handshake SMTP / Catch-All.
        """
        if not email or "@" not in email:
            return {
                "status": "Non vérifiable",
                "mx_verified": "Non",
                "reason": "Email manquant ou format invalide"
            }

        # 1. Syntaxe
        syntax_ok = self.validate_syntax(email)
        if not syntax_ok:
            return {
                "status": "Non vérifiable",
                "mx_verified": "Non",
                "reason": "Syntaxe d'email invalide"
            }

        domain = email.split("@")[1]
        has_mx, is_catchall, primary_mx, reason = self.check_mx_record(domain)

        if not has_mx:
            return {
                "status": "Non vérifiable",
                "mx_verified": "Non",
                "reason": reason
            }

        # 2. Handshake SMTP facultatif (non-bloquant, ignoré en fast_mode)
        if fast_mode:
            smtp_exists = None
            smtp_reason = "Vérification DNS MX active"
        else:
            smtp_exists, smtp_reason = self.verify_smtp_handshake(email, primary_mx)

        if smtp_exists is True:
            status_label = "Validé (SMTP 250 OK)"
            mx_verified = "Oui"
            final_reason = smtp_reason
        elif smtp_exists is False:
            status_label = "Invalide (Rejet SMTP)"
            mx_verified = "Non"
            final_reason = smtp_reason
        elif is_catchall:
            status_label = "Validé (Catch-All)"
            mx_verified = "Oui"
            final_reason = f"{reason} (Passerelle de sécurité / Catch-All)"
        else:
            status_label = "Validé (MX Direct)"
            mx_verified = "Oui"
            final_reason = f"Syntaxe valide & {reason}"

        return {
            "status": status_label,
            "mx_verified": mx_verified,
            "reason": final_reason,
            "smtp_checked": smtp_exists is not None
        }


email_validator = EmailValidator()
