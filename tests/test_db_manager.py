import pytest
import os
import tempfile
from storage.db_manager import DatabaseManager
from scrapers import Contact

class TestDatabaseManager:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = DatabaseManager(db_path=self.db_path)
    
    def teardown_method(self):
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def _create_contact(self, **kwargs) -> Contact:
        defaults = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'title': 'Responsable RH',
            'company': 'Thales',
            'linkedin_url': 'https://linkedin.com/in/jean-dupont',
            'email': 'jean.dupont@thalesgroup.com',
            'confidence_score': 85,
            'mx_status': 'valid',
            'mx_active': True,
        }
        defaults.update(kwargs)
        return Contact(**defaults)
    
    # Test database creation
    def test_db_created(self):
        assert os.path.exists(self.db_path)
    
    # Test insert
    def test_insert_contact(self):
        contact = self._create_contact()
        row_id = self.db.insert_contact(contact)
        assert row_id is not None
        assert row_id > 0
    
    # Test duplicate handling
    def test_insert_duplicate(self):
        contact = self._create_contact()
        id1 = self.db.insert_contact(contact)
        id2 = self.db.insert_contact(contact)  # Should update, not fail
        assert id1 is not None
        assert id2 is not None
    
    # Test retrieval
    def test_get_all_contacts(self):
        self.db.insert_contact(self._create_contact(first_name='Jean'))
        self.db.insert_contact(self._create_contact(first_name='Marie', linkedin_url='https://linkedin.com/in/marie-dupont'))
        contacts = self.db.get_all_contacts()
        assert len(contacts) == 2
    
    # Test filter by company
    def test_get_contacts_by_company(self):
        self.db.insert_contact(self._create_contact(company='Thales'))
        self.db.insert_contact(self._create_contact(company='Airbus', first_name='Pierre', linkedin_url='https://linkedin.com/in/pierre-dupont'))
        contacts = self.db.get_contacts_by_company('Thales')
        assert len(contacts) == 1
        assert contacts[0]['company'] == 'Thales'
    
    # Test stats
    def test_get_stats(self):
        self.db.insert_contact(self._create_contact())
        stats = self.db.get_stats()
        assert stats['total_contacts'] == 1
        assert 'by_company' in stats
        assert 'by_mx_status' in stats
    
    # Test search
    def test_search_contacts(self):
        self.db.insert_contact(self._create_contact(title='DRH'))
        results = self.db.search_contacts('DRH')
        assert len(results) == 1
    
    # Test context manager
    def test_context_manager(self):
        with DatabaseManager(db_path=self.db_path) as db:
            db.insert_contact(self._create_contact())
            contacts = db.get_all_contacts()
            assert len(contacts) >= 1
