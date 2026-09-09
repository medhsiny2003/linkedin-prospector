"""Main entry point for local execution."""

import argparse
import asyncio
import sys
from rich.console import Console
from rich.panel import Panel
from core.config import ProspectorConfig
from core.orchestrator import Orchestrator
from core.logger import setup_logger

logger = setup_logger("main")
console = Console()

async def main():
    parser = argparse.ArgumentParser(description="LinkedIn Prospector V3.2")
    parser.add_argument('--config', type=str, default='config/default.json', help='Path to configuration JSON file')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    
    args = parser.parse_args()
    
    console.print(Panel.fit("[bold blue]LinkedIn Prospector V3.2[/bold blue]", border_style="blue"))
    
    try:
        config = ProspectorConfig.from_json(args.config)
        logger.info(f"Loaded configuration from {args.config}")
        
        orchestrator = Orchestrator(config)
        
        if not args.resume:
            orchestrator.checkpoint.clear()
            
        stats = await orchestrator.run()
        
        console.print(Panel.fit(
            f"[bold green]Execution Complete[/bold green]\n"
            f"Companies Processed: {stats.get('total_companies_processed', 0)}\n"
            f"Contacts Extracted: {stats.get('total_contacts_extracted', 0)}\n"
            f"Failed Queries: {stats.get('failed_queries', 0)}\n"
            f"Results Excel: {stats.get('excel_export', 'N/A')}",
            title="Summary",
            border_style="green"
        ))
        
    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user. Checkpoint saved.")
        console.print("[bold yellow]Process gracefully stopped. Resume later using --resume flag.[/bold yellow]")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Fatal error during execution: {e}")
        console.print(f"[bold red]Fatal Error:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
