"""
Client réseau TLS haute fidélité avec émulation d'empreinte Chrome (curl_cffi).
Prend en charge les proxies résidentiels et gère les en-têtes réalistes.
"""

from typing import Any, Dict, Optional
import httpx
from config import config
from core.monitoring.audit_logger import audit_logger

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False


class TLSClient:
    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url or config.PROXY_URL
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        self.cookies: Dict[str, str] = {}

    def set_cookie(self, name: str, value: str) -> None:
        self.cookies[name] = value

    def get(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Dict[str, Any]:
        req_headers = {**self.headers, **(headers or {})}
        proxies = {"http": self.proxy_url, "https": self.proxy_url} if self.proxy_url else None

        if HAS_CURL_CFFI:
            try:
                resp = cffi_requests.get(
                    url,
                    headers=req_headers,
                    cookies=self.cookies,
                    proxies=proxies,
                    impersonate="chrome120",
                    timeout=timeout
                )
                return {
                    "status_code": resp.status_code,
                    "text": resp.text,
                    "headers": dict(resp.headers),
                    "url": str(resp.url)
                }
            except Exception as e:
                audit_logger.log_event("TLS_CLIENT_ERROR", f"Échec curl_cffi, tentative de fallback httpx : {e}")

        # Fallback HTTPX
        with httpx.Client(proxies=self.proxy_url, headers=req_headers, cookies=self.cookies, timeout=timeout) as client:
            resp = client.get(url)
            return {
                "status_code": resp.status_code,
                "text": resp.text,
                "headers": dict(resp.headers),
                "url": str(resp.url)
            }


tls_client = TLSClient()
