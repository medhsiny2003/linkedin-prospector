"""Main orchestrator for the LinkedIn Prospector V3.2.

Coordinates scraping, enrichment, validation, storage, and export.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from .config import ProspectorConfig
from .logger import setup_logger
from .rate_limiter import RateLimiter
from .checkpoint import CheckpointManager

from scrapers import Contact
from scrapers.hybrid_scraper import HybridScraper
from enricher.email_generator import EmailGenerator
from enricher.email_validator import EmailValidator
from enricher.pattern_detector import PatternDetector
from storage.db_manager import DatabaseManager
from storage.exporter import ExcelExporter

logger = setup_logger(__name__)


class Orchestrator:
    """Coordinates the full LinkedIn Prospector pipeline.

    Flow:
        1. Load config → init all modules
        2. Check for checkpoint → resume if available
        3. For each (company, keyword):
           a. Scrape via X-Ray, fallback to Stealth
           b. Generate email candidates
           c. Validate emails (syntax + MX, optional SMTP)
           d. Score contacts
           e. Save to SQLite immediately
           f. Update checkpoint
        4. Export to Excel + JSON
        5. Return summary stats
    """

    def __init__(self, config: ProspectorConfig):
        self.config = config

        # --- Sub-components ---
        self.rate_limiter = RateLimiter(
            rpm=config.rate_limit_rpm,
            min_delay=config.min_delay,
            max_delay=config.max_delay,
            circuit_breaker_threshold=config.circuit_breaker_threshold,
        )
        self.scraper = HybridScraper(config=config, rate_limiter=self.rate_limiter)
        self.email_gen = EmailGenerator()
        self.email_validator = EmailValidator()
        self.pattern_detector = PatternDetector()

        # Persistence
        os.makedirs(os.path.dirname(config.db_path) or "data", exist_ok=True)
        self.db = DatabaseManager(db_path=config.db_path)
        self.exporter = ExcelExporter()

        # Checkpoint
        checkpoint_path = os.path.join(
            os.path.dirname(config.db_path) or "data", "checkpoint.json"
        )
        self.checkpoint = CheckpointManager(checkpoint_path=checkpoint_path)

        # Load company-domain mapping
        self.company_domains = self._load_company_domains()

        # Counters
        self.total_contacts_processed = 0
        self.current_contact_id = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> Dict[str, Any]:
        """Run the main extraction workflow. Returns a summary dict."""
        logger.info("═" * 60)
        logger.info("  LinkedIn Prospector V3.2 — Starting")
        logger.info("═" * 60)
        logger.info(
            f"Companies: {len(self.config.companies)} | "
            f"Keywords: {len(self.config.keywords)} | "
            f"Location: {self.config.location}"
        )

        # Try to load pattern cache
        self.pattern_detector.load_cache()

        # Resume logic
        resume_point = self.checkpoint.get_resume_point()
        start_company: Optional[str] = resume_point[0] if resume_point else None
        start_keyword: Optional[str] = resume_point[1] if resume_point else None

        if start_company:
            logger.info(
                f"⏩ Resuming from checkpoint: company={start_company}, keyword={start_keyword}"
            )

        skip_company = bool(start_company)

        try:
            for company in self.config.companies:
                if skip_company and company != start_company:
                    continue
                skip_company = False

                logger.info(f"▶ Processing company: {company}")
                await self._process_company(
                    company,
                    start_keyword if company == start_company else None,
                )
                start_keyword = None  # only applies to the first resumed company

                # Rate limit between companies
                await self.rate_limiter.wait()

        except KeyboardInterrupt:
            logger.warning("Interrupted by user — checkpoint saved.")
            raise
        finally:
            # Always close the stealth browser if it was opened
            await self.scraper.close()
            self.pattern_detector.save_cache()

        # Export results
        logger.info("📦 Exporting results…")
        excel_path = self._export_results()
        json_path = self._generate_results_json()

        stats = {
            "total_companies_processed": len(
                self.checkpoint.state.get("processed_companies", [])
            ),
            "total_contacts_extracted": self.total_contacts_processed,
            "failed_queries": len(
                self.checkpoint.state.get("failed_queries", [])
            ),
            "excel_export": excel_path,
            "json_export": json_path,
            "rate_limiter": self.rate_limiter.get_stats(),
            "db_stats": self.db.get_stats(),
        }

        # Write summary JSON for GitHub Actions
        summary_path = os.path.join(self.config.output_dir, "summary.json")
        os.makedirs(self.config.output_dir, exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"✅ Run complete — {self.total_contacts_processed} contacts extracted")
        self.checkpoint.clear()
        return stats

    # ------------------------------------------------------------------
    # Company / keyword processing
    # ------------------------------------------------------------------

    async def _process_company(
        self, company: str, start_keyword: Optional[str] = None
    ) -> List[Contact]:
        """Process all keywords for a given company."""
        all_contacts: List[Contact] = []
        skip_keyword = bool(start_keyword)
        consecutive_failures = 0

        for keyword in self.config.keywords:
            if skip_keyword and keyword != start_keyword:
                continue
            skip_keyword = False

            logger.info(f"  🔎 Searching: '{keyword}' @ {company}")
            try:
                if self.rate_limiter.is_circuit_open():
                    logger.warning("Circuit breaker is open — pausing.")
                await self.rate_limiter.wait()

                contacts = await self._process_keyword(company, keyword)
                all_contacts.extend(contacts)
                self.rate_limiter.record_success()
                consecutive_failures = 0

                self.checkpoint.update_progress(
                    company=company,
                    keyword=keyword,
                    contact_id=self.current_contact_id,
                    total=self.total_contacts_processed,
                )
                
                logger.info(f"    [Metrics] Success: {len(contacts)} new profiles. Total processed: {self.total_contacts_processed}. Current company progress saved.")

            except Exception as exc:
                logger.error(f"Error processing {company} / {keyword}: {exc}")
                self.rate_limiter.record_failure()
                self.checkpoint.mark_failed(f"{company}:{keyword}")
                consecutive_failures += 1
                
                if consecutive_failures >= 3:
                    logger.warning(f"Circuit Breaker Triggered: 3 consecutive failures for {company}. Pausing 5 minutes and skipping to next company.")
                    await asyncio.sleep(300)
                    break

        # Save state after completing all keywords for this company
        if self.config.keywords:
            self.checkpoint.update_progress(
                company=company,
                keyword=self.config.keywords[-1],
                contact_id=self.current_contact_id,
                total=self.total_contacts_processed,
            )

        return all_contacts

    async def _process_keyword(
        self, company: str, keyword: str
    ) -> List[Contact]:
        """Scrape + enrich + validate + save contacts for one (company, keyword) pair."""
        raw_contacts = await self.scraper.search(
            company=company,
            keywords=[keyword],
            location=self.config.location,
        )
        logger.info(f"    Found {len(raw_contacts)} raw profiles")

        processed: List[Contact] = []

        for contact in raw_contacts:
            self.current_contact_id += 1

            # Enrich: generate email candidates
            enriched = self._enrich_contact(contact, company)

            # Validate: syntax + MX (+ optional SMTP)
            validated = await self._validate_and_score(enriched)

            # Persist immediately
            self._save_contact(validated)
            processed.append(validated)
            self.total_contacts_processed += 1

        return processed

    # ------------------------------------------------------------------
    # Enrichment helpers
    # ------------------------------------------------------------------

    def _enrich_contact(self, contact: Contact, company: str) -> Contact:
        """Generate email candidates for the contact."""
        domain = self._resolve_domain(company)
        if not domain:
            logger.warning(f"    No domain found for {company} — skipping email generation")
            return contact

        # Check if we have a known pattern for this domain
        known_pattern = self.pattern_detector.get_cached_pattern(domain)

        emails = self.email_gen.generate(
            first_name=contact.first_name,
            last_name=contact.last_name,
            domain=domain,
            level=self.config.email_level,
        )

        if not emails:
            return contact

        # Primary email = highest score
        contact.email = emails[0][0]
        contact.confidence_score = emails[0][1]

        # Alternatives
        if len(emails) > 1:
            contact.email_alt1 = emails[1][0]
        if len(emails) > 2:
            contact.email_alt2 = emails[2][0]

        return contact

    async def _validate_and_score(self, contact: Contact) -> Contact:
        """Validate the primary email and adjust the confidence score."""
        if not contact.email:
            contact.mx_status = "unknown"
            return contact

        try:
            # Only do SMTP check for high-confidence leads
            check_smtp = (
                self.config.enable_smtp_check and contact.confidence_score >= 80
            )

            result = await self.email_validator.validate(
                contact.email, check_smtp=check_smtp
            )

            contact.mx_status = result["status"]
            contact.mx_active = bool(result.get("mx_active"))

            # Adjust confidence based on validation
            if result["status"] == "valid":
                # MX is valid — keep or slightly boost score
                contact.confidence_score = min(
                    contact.confidence_score + 5, 99
                )
            elif result["status"] == "catch-all":
                # Catch-all domains: lower confidence
                contact.confidence_score = max(
                    contact.confidence_score - 20, 20
                )
                contact.mx_status = "catch-all"
            elif result["status"] == "invalid":
                contact.confidence_score = max(
                    contact.confidence_score - 40, 5
                )
                contact.mx_status = "invalid"

        except Exception as exc:
            logger.warning(f"    Validation error for {contact.email}: {exc}")
            contact.mx_status = "unknown"

        return contact

    # ------------------------------------------------------------------
    # Persistence & export
    # ------------------------------------------------------------------

    def _save_contact(self, contact: Contact) -> None:
        """Immediately save contact to the database."""
        try:
            self.db.insert_contact(contact)
        except Exception as exc:
            logger.error(f"    DB save error: {exc}")

    def _export_results(self) -> str:
        """Export all stored contacts to a timestamped Excel file."""
        os.makedirs(self.config.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(
            self.config.output_dir, f"linkedin_prospects_{timestamp}.xlsx"
        )
        contacts = self.db.export_to_dicts()
        return self.exporter.export(contacts, output_path=path)

    def _generate_results_json(self) -> str:
        """Export all stored contacts to a JSON file for the web UI."""
        os.makedirs(self.config.output_dir, exist_ok=True)
        path = os.path.join(self.config.output_dir, "results.json")
        contacts = self.db.export_to_dicts()
        return self.exporter.export_json(contacts, output_path=path)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _resolve_domain(self, company: str) -> Optional[str]:
        """Resolve a company name to its email domain."""
        # Exact match
        if company in self.company_domains:
            return self.company_domains[company]

        # Case-insensitive match
        for name, domain in self.company_domains.items():
            if name.lower() == company.lower():
                return domain

        # Fallback: sanitize company name into a plausible domain
        slug = company.lower().replace(" ", "").replace("'", "")
        return f"{slug}.com"

    def _load_company_domains(self) -> Dict[str, str]:
        """Load the company→domain mapping from config/company_domains.json."""
        path = os.path.join("config", "company_domains.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning(f"Could not load company_domains.json: {exc}")
        return {}
