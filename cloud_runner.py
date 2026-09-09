"""GitHub Actions entry point for LinkedIn Prospector."""

import os
import json
import asyncio
import sys
from core.config import ProspectorConfig
from core.orchestrator import Orchestrator
from core.logger import setup_logger

logger = setup_logger("cloud_runner")

async def main():
    logger.info("Starting Cloud Runner (GitHub Actions mode)")
    
    # Check if config is provided via environment variable
    config_json_str = os.getenv("CONFIG_JSON")
    
    try:
        if config_json_str:
            logger.info("Loading config from CONFIG_JSON environment variable")
            config_data = json.loads(config_json_str)
            config = ProspectorConfig(**config_data)
        else:
            config_path = os.getenv("CONFIG_PATH", "config/default.json")
            logger.info(f"Loading config from file: {config_path}")
            config = ProspectorConfig.from_json(config_path)
            
        # Ensure output directory exists for GitHub artifacts
        os.makedirs(config.output_dir, exist_ok=True)
        
        orchestrator = Orchestrator(config)
        stats = await orchestrator.run()
        
        # Output to GitHub Step Summary if running in Actions
        summary_file = os.getenv("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a", encoding="utf-8") as f:
                f.write("## LinkedIn Prospector Run Summary\n\n")
                f.write(f"- **Companies Processed:** {stats.get('total_companies_processed', 0)}\n")
                f.write(f"- **Contacts Extracted:** {stats.get('total_contacts_extracted', 0)}\n")
                f.write(f"- **Failed Queries:** {stats.get('failed_queries', 0)}\n")
                f.write(f"- **Artifacts Available:** `results.xlsx`, `results.json`\n")
                
        logger.info("Cloud execution completed successfully")
        
    except Exception as e:
        logger.exception(f"Fatal error during cloud execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
