"""Local Web Server & GUI Backend for LinkedIn Prospector V3.2."""

import os
import sys
import json
import socket
import asyncio
import webbrowser
import logging
from datetime import datetime

# Configure safe UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from aiohttp import web

# Adjust path to import core modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import ProspectorConfig
from core.orchestrator import Orchestrator
from storage.db_manager import DatabaseManager

# Global state
app_state = {
    "status": "idle",  # idle, running, completed, error
    "logs": [],
    "progress": {"company": "", "keyword": "", "total_contacts": 0},
    "stats": {},
    "current_task": None
}

class WebLogHandler(logging.Handler):
    """Custom logging handler to send logs to Web UI in real-time."""
    def emit(self, record):
        try:
            msg = self.format(record)
            entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "level": record.levelname,
                "message": msg
            }
            app_state["logs"].append(entry)
            if len(app_state["logs"]) > 300:
                app_state["logs"].pop(0)
        except Exception:
            pass

# Attach logger
web_handler = WebLogHandler()
web_handler.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger().addHandler(web_handler)


async def run_pipeline_task(config: ProspectorConfig):
    """Run orchestrator in background."""
    global app_state
    try:
        app_state["status"] = "running"
        app_state["logs"].append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": "INFO",
            "message": "Demarrage de la prospection..."
        })
        
        orchestrator = Orchestrator(config)
        stats = await orchestrator.run()
        
        app_state["status"] = "completed"
        app_state["stats"] = stats
        app_state["logs"].append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": "SUCCESS",
            "message": f"Prospection terminee avec succes ! {stats.get('total_contacts_extracted', 0)} contacts extraits."
        })
    except asyncio.CancelledError:
        app_state["status"] = "idle"
        app_state["logs"].append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": "WARNING",
            "message": "Prospection arretee par l'utilisateur."
        })
    except Exception as e:
        app_state["status"] = "error"
        app_state["logs"].append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": "ERROR",
            "message": f"Erreur: {str(e)}"
        })


# --- API Routes ---

async def handle_status(request):
    """Get current running status and logs."""
    return web.json_response({
        "status": app_state["status"],
        "logs": app_state["logs"],
        "progress": app_state["progress"],
        "stats": app_state["stats"]
    })


async def handle_start(request):
    """Start prospection with given config."""
    global app_state
    if app_state["status"] == "running":
        return web.json_response({"error": "Une prospection est deja en cours"}, status=400)
    
    try:
        data = await request.json()
        
        # Merge with default config
        config = ProspectorConfig.from_json("config/default.json")
        if "companies" in data and data["companies"]:
            config.companies = data["companies"]
        if "keywords" in data and data["keywords"]:
            config.keywords = data["keywords"]
        if "location" in data and data["location"]:
            config.location = data["location"]
        if "email_level" in data:
            config.email_level = data["email_level"]
        if "max_results" in data:
            config.max_results_per_company = int(data["max_results"])
        if "enable_smtp_check" in data:
            config.enable_smtp_check = bool(data["enable_smtp_check"])

        app_state["logs"] = []
        app_state["current_task"] = asyncio.create_task(run_pipeline_task(config))
        return web.json_response({"status": "started", "message": "Prospection lancee avec succes"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_stop(request):
    """Stop currently running prospection."""
    global app_state
    if app_state["current_task"] and not app_state["current_task"].done():
        app_state["current_task"].cancel()
        app_state["status"] = "idle"
        return web.json_response({"status": "stopped", "message": "Prospection arretee"})
    return web.json_response({"status": "not_running", "message": "Aucune tache en cours"})


async def handle_results(request):
    """Get all extracted contacts from SQLite."""
    try:
        db = DatabaseManager(db_path="data/prospector.db")
        contacts = db.get_all_contacts()
        db.close()
        return web.json_response({"contacts": contacts})
    except Exception as e:
        return web.json_response({"contacts": [], "error": str(e)})


async def handle_open_folder(request):
    """Open output folder in Windows Explorer."""
    os.makedirs("output", exist_ok=True)
    os.system(f'explorer "{os.path.abspath("output")}"')
    return web.json_response({"status": "opened"})


def is_port_available(port: int) -> bool:
    """Check if a TCP port is free on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def find_free_port(preferred_ports=(5000, 5001, 8000, 8080, 8888)) -> int:
    """Find the first available port from the preferred list."""
    for p in preferred_ports:
        if is_port_available(p):
            return p
    # Fallback to dynamic port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def create_app():
    app = web.Application()
    
    # API Endpoints
    app.router.add_get('/api/status', handle_status)
    app.router.add_post('/api/start', handle_start)
    app.router.add_post('/api/stop', handle_stop)
    app.router.add_get('/api/results', handle_results)
    app.router.add_post('/api/open_folder', handle_open_folder)
    
    # Static files (Web UI)
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
    app.router.add_static('/', app_dir, show_index=True)
    
    return app


async def start_server():
    port = find_free_port()
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '127.0.0.1', port)
    await site.start()
    
    url = f"http://localhost:{port}/index.html"
    print("")
    print("=" * 65)
    print("      LinkedIn Prospector V3.2 - Application Active")
    print("=" * 65)
    print(f"  Interface Web : {url}")
    print("  (Laissez cette fenetre ouverte tant que vous utilisez l'outil)")
    print("=" * 65)
    print("")
    
    # Open browser automatically
    try:
        webbrowser.open(url)
    except Exception:
        pass

    # Wait indefinitely
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await runner.cleanup()


def main():
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("\n[INFO] Serveur arrete par l'utilisateur.")
    except Exception as e:
        print(f"\n[ERREUR] Erreur inattendue : {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
