import asyncio
import smtplib
import socket
from typing import Dict, List, Any
import dns.resolver
from email_validator import validate_email, EmailNotValidError

class EmailValidator:
    """Validates email addresses across 3 tiers: Syntax RFC, DNS MX, and optional non-intrusive SMTP."""

    def __init__(self, smtp_from: str = 'verify@example.com', timeout: int = 5):
        self.smtp_from = smtp_from
        self.timeout = timeout
        self.mx_cache: Dict[str, list] = {}

    async def validate(self, email: str, check_smtp: bool = False) -> Dict[str, Any]:
        """Validates an email address and returns a comprehensive status dictionary."""
        result = {
            'email': email,
            'syntax_valid': False,
            'mx_valid': False,
            'mx_records': [],
            'mx_active': '',
            'smtp_valid': None,
            'is_catch_all': None,
            'status': 'unknown'
        }

        # Step 1: Syntax Validation
        try:
            validate_email(email, check_deliverability=False)
            result['syntax_valid'] = True
        except EmailNotValidError:
            result['status'] = 'invalid'
            return result
        except Exception:
            result['status'] = 'invalid'
            return result

        if '@' not in email:
            result['status'] = 'invalid'
            return result

        domain = email.split('@')[1].strip()
        if not domain or '.' not in domain:
            result['status'] = 'invalid'
            return result

        # Step 2: DNS MX Resolution
        if domain in self.mx_cache:
            mx_records = self.mx_cache[domain]
        else:
            try:
                loop = asyncio.get_event_loop()
                answers = await loop.run_in_executor(None, dns.resolver.resolve, domain, 'MX')
                mx_records = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in answers])
                self.mx_cache[domain] = mx_records
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, Exception):
                self.mx_cache[domain] = []
                mx_records = []

        if mx_records:
            result['mx_valid'] = True
            result['mx_records'] = mx_records
            result['mx_active'] = mx_records[0][1] if mx_records else ''
            result['status'] = 'valid'
        else:
            result['status'] = 'invalid'
            return result

        # Step 3: Optional Non-Intrusive SMTP & Catch-All Probe
        if check_smtp and result['mx_valid'] and result['mx_active']:
            smtp_result = await self._check_smtp(email, result['mx_active'], domain)
            result['smtp_valid'] = smtp_result['valid']
            result['is_catch_all'] = smtp_result['catch_all']
            if smtp_result['catch_all']:
                result['status'] = 'catch-all'
            elif not smtp_result['valid']:
                result['status'] = 'invalid'

        return result

    async def _check_smtp(self, email: str, mx_host: str, domain: str) -> Dict[str, bool]:
        """Performs non-intrusive RCPT TO verification and catch-all probing."""
        fake_email = f"probe_check_nonexistent_xyz_{socket.gethostname()}@{domain}"
        loop = asyncio.get_event_loop()

        def run_check():
            try:
                server = smtplib.SMTP(timeout=self.timeout)
                server.connect(mx_host)
                server.helo(socket.getfqdn())
                server.mail(self.smtp_from)
                
                code, _ = server.rcpt(email)
                valid = (code == 250)

                # Catch-all detection: probe nonexistent mailbox
                fake_code, _ = server.rcpt(fake_email)
                catch_all = (fake_code == 250) and valid

                server.quit()
                return {'valid': valid, 'catch_all': catch_all}
            except Exception:
                return {'valid': False, 'catch_all': False}

        return await loop.run_in_executor(None, run_check)

    async def validate_batch(self, emails: List[str], check_smtp: bool = False) -> List[Dict[str, Any]]:
        """Validates a batch of email addresses concurrently with bounded concurrency."""
        semaphore = asyncio.Semaphore(10)

        async def bounded_validate(e):
            async with semaphore:
                return await self.validate(e, check_smtp=check_smtp)

        tasks = [bounded_validate(e) for e in emails]
        return await asyncio.gather(*tasks)
