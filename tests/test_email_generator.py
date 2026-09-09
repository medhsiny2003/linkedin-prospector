# Comprehensive tests for EmailGenerator
import pytest
from enricher.email_generator import EmailGenerator

class TestEmailGenerator:
    def setup_method(self):
        self.generator = EmailGenerator()
    
    # Test name normalization
    def test_normalize_simple_name(self):
        assert self.generator._normalize_name('Jean') == 'jean'
    
    def test_normalize_accented_name(self):
        assert self.generator._normalize_name('François') == 'francois'
        assert self.generator._normalize_name('Héloïse') == 'heloise'
        assert self.generator._normalize_name('André') == 'andre'
    
    def test_normalize_compound_name(self):
        assert self.generator._normalize_name('Jean-Pierre') == 'jeanpierre'
    
    def test_normalize_special_chars(self):
        assert self.generator._normalize_name("O'Brien") == 'obrien'
    
    # Test email generation - Light level
    def test_generate_light_count(self):
        emails = self.generator.generate('Jean', 'Dupont', 'example.com', level='light')
        assert len(emails) == 4
    
    def test_generate_light_patterns(self):
        emails = self.generator.generate('Jean', 'Dupont', 'example.com', level='light')
        email_addresses = [e[0] for e in emails]
        assert 'jean.dupont@example.com' in email_addresses
        assert 'jeandupont@example.com' in email_addresses
        assert 'j.dupont@example.com' in email_addresses
        assert 'jean.d@example.com' in email_addresses
    
    # Test email generation - Medium level
    def test_generate_medium_count(self):
        emails = self.generator.generate('Marie', 'Martin', 'test.fr', level='medium')
        assert len(emails) == 11
    
    def test_generate_medium_includes_light(self):
        emails = self.generator.generate('Marie', 'Martin', 'test.fr', level='medium')
        email_addresses = [e[0] for e in emails]
        assert 'marie.martin@test.fr' in email_addresses  # Light pattern
        assert 'martin.marie@test.fr' in email_addresses  # Medium pattern
    
    # Test email generation - Heavy level  
    def test_generate_heavy_count(self):
        emails = self.generator.generate('Pierre', 'Durand', 'corp.com', level='heavy')
        assert len(emails) == 22
    
    # Test score ordering
    def test_scores_descending(self):
        emails = self.generator.generate('Test', 'User', 'example.com', level='heavy')
        scores = [e[1] for e in emails]
        assert scores == sorted(scores, reverse=True)
    
    # Test best email
    def test_get_best_email(self):
        email, score = self.generator.get_best_email('Jean', 'Dupont', 'example.com')
        assert email == 'jean.dupont@example.com'
        assert score == 95
    
    # Test top N
    def test_get_top_n(self):
        results = self.generator.get_top_n_emails('Jean', 'Dupont', 'example.com', n=3)
        assert len(results) == 3
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
    
    # Test with accented names
    def test_accented_name_generation(self):
        emails = self.generator.generate('François', 'Müller', 'example.com', level='light')
        email_addresses = [e[0] for e in emails]
        assert 'francois.muller@example.com' in email_addresses
    
    # Test empty inputs
    def test_empty_first_name(self):
        emails = self.generator.generate('', 'Dupont', 'example.com')
        assert len(emails) == 0 or all('@' in e[0] for e in emails)
    
    def test_empty_domain(self):
        emails = self.generator.generate('Jean', 'Dupont', '')
        assert len(emails) == 0
