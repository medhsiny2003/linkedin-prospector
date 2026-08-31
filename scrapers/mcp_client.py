"""
Client MCP (Model Context Protocol) optionnel pour LinkedIn.
Permet d'interroger un serveur MCP local ou distant (FastMCP / linkedin-spider).
Activable via USE_MCP_SERVER=true dans le fichier .env.
"""

import json
from typing import Any, Dict, List, Optional
import httpx
from config import config
from core.monitoring.audit_logger import audit_logger


class MCPClient:
    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or config.MCP_SERVER_URL
        self.is_enabled = config.USE_MCP_SERVER

    async def search_profiles(
        self,
        keywords: str,
        company: str = "",
        location: str = "France",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Exécute l'outil de recherche de profils via le serveur MCP.
        """
        if not self.is_enabled:
            return []

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_linkedin_profiles",
                "arguments": {
                    "keywords": keywords,
                    "company": company,
                    "location": location,
                    "limit": limit
                }
            },
            "id": 1
        }

        try:
            audit_logger.log_event("MCP_CALL", f"Appel MCP vers {self.server_url} pour {company} - {keywords}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.server_url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("result", {}).get("content", [])
                    audit_logger.log_event("MCP_SUCCESS", f"{len(results)} profils renvoyés par le serveur MCP.")
                    return results
                else:
                    audit_logger.log_event("MCP_WARN", f"Le serveur MCP a répondu : {response.status_code}")
        except Exception as e:
            audit_logger.log_event("MCP_ERROR", f"Échec de communication avec le serveur MCP : {e}")

        return []


mcp_client = MCPClient()
