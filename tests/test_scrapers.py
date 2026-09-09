import pytest
from scrapers.parsers.dom_parser import DOMParser
from scrapers.parsers.strategy_parser import StrategyParser
from scrapers import Contact

class TestDOMParser:
    def setup_method(self):
        self.parser = DOMParser()
    
    # Test LinkedIn title parsing
    def test_parse_full_title(self):
        result = self.parser.parse_linkedin_title('Jean Dupont - Responsable RH - Thales | LinkedIn')
        assert result['first_name'] == 'Jean'
        assert result['last_name'] == 'Dupont'
        assert result['title'] == 'Responsable RH'
        assert result['company'] == 'Thales'
    
    def test_parse_title_no_company(self):
        result = self.parser.parse_linkedin_title('Marie Martin - Recruteuse | LinkedIn')
        assert result['first_name'] == 'Marie'
        assert result['last_name'] == 'Martin'
        assert result['title'] == 'Recruteuse'
    
    def test_parse_title_name_only(self):
        result = self.parser.parse_linkedin_title('Pierre Durand | LinkedIn')
        assert result['first_name'] == 'Pierre'
        assert result['last_name'] == 'Durand'
    
    # Test name cleaning
    def test_clean_simple_name(self):
        first, last = self.parser.clean_name('Jean Dupont')
        assert first == 'Jean'
        assert last == 'Dupont'
    
    def test_clean_compound_name(self):
        first, last = self.parser.clean_name('Jean-Pierre de la Fontaine')
        assert first == 'Jean-Pierre'
        assert 'Fontaine' in last
    
    def test_clean_three_part_name(self):
        first, last = self.parser.clean_name('Marie Claire Dupont')
        assert first == 'Marie'
        # last should contain remaining parts

class TestStrategyParser:
    def test_xray_sufficient(self):
        strategy = StrategyParser.determine_strategy('Thales', 10, True)
        assert strategy == 'xray_only'
    
    def test_stealth_fallback(self):
        strategy = StrategyParser.determine_strategy('Thales', 2, True)
        assert strategy == 'stealth_fallback'
    
    def test_no_cookie_stays_xray(self):
        strategy = StrategyParser.determine_strategy('Thales', 2, False)
        assert strategy == 'xray_only'
    
    def test_should_expand(self):
        assert StrategyParser.should_expand_search(5, 50) == True
        assert StrategyParser.should_expand_search(30, 50) == False
    
    def test_optimize_keywords(self):
        results = {'RH': 10, 'Manager': 0, 'Recruteur': 5}
        optimized = StrategyParser.optimize_keywords(['RH', 'Manager', 'Recruteur'], results)
        assert 'Manager' not in optimized
        assert optimized[0] == 'RH'  # Most results first

class TestContactDataclass:
    def test_create_contact(self):
        contact = Contact(first_name='Jean', last_name='Dupont', company='Thales')
        assert contact.first_name == 'Jean'
        assert contact.mx_status == 'unknown'
        assert contact.source == 'xray'
    
    def test_contact_defaults(self):
        contact = Contact()
        assert contact.first_name == ''
        assert contact.confidence_score == 0
        assert contact.extraction_date  # Should have a default datetime
