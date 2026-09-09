import asyncio
import smtplib
import socket
from typing import Dict, List, Optional
import dns.resolver
from email_validator import validate_email, EmailNotValidError

class EmailValidator:
    def __init__(self, smtp_from: str = 'verify@example.com', timeout: int = 10):
        self.smtp_from = smtp_from
        self.timeout = timeout

    async def validate(self, email: str, check_smtp: bool = False) -> Dict:
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

        try:
            validate_email(email, check_deliverability=False)
            result['syntax_valid'] = True
        except EmailNotValidError:
            result['status'] = 'invalid'
            return result

        domain = email.split('@')[1]
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            result['mx_records'] = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in mx_records])
            result['mx_valid'] = True
            result['mx_active'] = result['mx_records'][0][1] if result['mx_records'] else ''
            result['status'] = 'valid'
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, Exception):
            result['status'] = 'invalid'
            return result

        if check_smtp and result['mx_valid'] and result['mx_active']:
            smtp_result = await self._check_smtp(email, result['mx_active'])
            result['smtp_valid'] = smtp_result['valid']
            result['is_catch_all'] = smtp_result['catch_all']
            if smtp_result['catch_all']:
                result['status'] = 'catch-all'
            elif not smtp_result['valid']:
                result['status'] = 'invalid'

        return result

    async def _check_smtp(self, email: str, mx_host: str) -> Dict:
        domain = email.split('@')[1]
        fake_email = f"invalid_random_{socket.gethostname()}@{domain}"
        
        loop = asyncio.get_event_loop()
        
        def run_smtp_check():
            try:
                server = smtplib.SMTP(timeout=self.timeout)
                server.connect(mx_host)
                server.helo(socket.gethostname())
                server.mail(self.smtp_from)
                code, _ = server.rcpt(email)
                valid = (code == 250)
                
                fake_code, _ = server.rcpt(fake_email)
                catch_all = (fake_code == 250) and valid
                
                server.quit()
                return {'valid': valid, 'catch_all': catch_all}
            except Exception:
                return {'valid': False, 'catch_all': False}

        return await loop.run_in_executor(None, run_smtp_check)

    async def validate_batch(self, emails: List[str], check_smtp: bool = False) -> List[Dict]:
        semaphore = asyncio.Semaphore(5)
        
        async def bounded_validate(email):
            async with semaphore:
                return await self.validate(email, check_smtp)
                
        tasks = [bounded_validate(email) for email in emails]
        return await asyncio.gather(*tasks)
