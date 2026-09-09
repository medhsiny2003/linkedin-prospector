import pytest
import asyncio
from enricher.email_validator import EmailValidator

class TestEmailValidator:
    def setup_method(self):
        self.validator = EmailValidator()
    
    # Test syntax validation
    def test_valid_syntax(self):
        result = asyncio.run(self.validator.validate('test@example.com'))
        assert result['syntax_valid'] == True
    
    def test_invalid_syntax_no_at(self):
        result = asyncio.run(self.validator.validate('testexample.com'))
        assert result['syntax_valid'] == False
        assert result['status'] == 'invalid'
    
    def test_invalid_syntax_no_domain(self):
        result = asyncio.run(self.validator.validate('test@'))
        assert result['syntax_valid'] == False
    
    def test_invalid_syntax_spaces(self):
        result = asyncio.run(self.validator.validate('test @example.com'))
        assert result['syntax_valid'] == False
    
    # Test MX validation (requires network, mark with marker)
    @pytest.mark.skipif(True, reason='Requires network access')
    def test_mx_valid_gmail(self):
        result = asyncio.run(self.validator.validate('test@gmail.com'))
        assert result['mx_valid'] == True
        assert len(result['mx_records']) > 0
    
    @pytest.mark.skipif(True, reason='Requires network access')
    def test_mx_invalid_domain(self):
        result = asyncio.run(self.validator.validate('test@thisisnotarealdomainxyz123.com'))
        assert result['mx_valid'] == False
    
    # Test batch validation
    def test_validate_batch(self):
        emails = ['test@example.com', 'invalid', 'user@test.org']
        results = asyncio.run(self.validator.validate_batch(emails))
        assert len(results) == 3
        assert results[1]['syntax_valid'] == False
    
    # Test result structure
    def test_result_keys(self):
        result = asyncio.run(self.validator.validate('test@example.com'))
        expected_keys = {'email', 'syntax_valid', 'mx_valid', 'mx_records', 'mx_active', 'smtp_valid', 'is_catch_all', 'status'}
        assert set(result.keys()) == expected_keys
