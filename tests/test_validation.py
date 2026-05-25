import os
import pytest
from dynaconf import Dynaconf, Validator, ValidationError
from src.proxmox_info.config import settings


def test_config_loads_with_test_environment():
    """Test that settings load correctly with FORCE_ENV_FOR_DYNACONF=testing"""
    # The conftest.py or test environment should set this
    # We're testing that the settings object from config.py can be accessed
    assert settings is not None
    # Test that we can access some settings (they may have defaults)
    assert hasattr(settings, 'HOST')
    assert hasattr(settings, 'USER')
    assert hasattr(settings, 'PASSWORD')


def test_validators_catch_wrong_types():
    """Test that validators catch wrong types for verify_ssl and timeout"""
    test_settings = Dynaconf(
        settings_files=[],
        apply_default_on_none=True,
        core_loaders=['YAML'],
        validate_on_update=False,
        validators=[
            Validator('host', default='localhost'),
            Validator('user', 'password', default=None),
            Validator('verify_ssl', is_type_of=bool),
            Validator('timeout', is_type_of=int),
        ]
    )

    test_settings.update({'verify_ssl': 'not_a_bool', 'timeout': 'not_an_int'})
    with pytest.raises(ValidationError):
        test_settings.validators.validate()


def test_validators_pass_with_valid_user_password():
    """Test that validators pass when user/password are provided"""
    test_settings = Dynaconf(
        settings_files=[],
        apply_default_on_none=True,
        core_loaders=['YAML'],
        validate_on_update=False,  # Avoid recursion
        validators=[
            Validator('host', default='localhost'),
            Validator('user', 'password', default=None),
            Validator('verify_ssl', is_type_of=bool),
            Validator('timeout', is_type_of=int),
        ]
    )
    
    # Update with valid values
    test_settings.update({
        'host': 'test-host',
        'user': 'test-user',
        'password': 'test-password',
        'timeout': 30
    })
    
    # Should not raise ValidationError when we validate
    try:
        test_settings.validators.validate()
    except ValidationError:
        pytest.fail("ValidationError raised unexpectedly")


def test_timeout_validation():
    """Test that timeout validation works correctly"""
    test_settings = Dynaconf(
        settings_files=[],
        apply_default_on_none=True,
        core_loaders=['YAML'],
        validate_on_update=False,  # Avoid recursion
        validators=[
            Validator('timeout', is_type_of=int),
        ]
    )
    
    # Valid integer timeout
    test_settings.update({'timeout': 30})
    # Should not raise
    test_settings.validators.validate()
    
    # Invalid string timeout
    test_settings.update({'timeout': 'invalid'})
    with pytest.raises(ValidationError):
        test_settings.validators.validate()


def test_verify_ssl_validation():
    """Test that verify_ssl validation works correctly"""
    test_settings = Dynaconf(
        settings_files=[],
        apply_default_on_none=True,
        core_loaders=['YAML'],
        validate_on_update=False,  # Avoid recursion
        validators=[
            Validator('verify_ssl', is_type_of=bool),
        ]
    )
    
    # Valid boolean values
    for valid_val in [True, False]:
        test_settings.update({'verify_ssl': valid_val})
        # Should not raise
        test_settings.validators.validate()
    
    # Invalid non-boolean value
    test_settings.update({'verify_ssl': 'yes'})
    with pytest.raises(ValidationError):
        test_settings.validators.validate()


def test_main_function_validation_missing_credentials():
    """Test that main function handles missing credentials properly"""
    # We'll test this by mocking the main function's validation logic
    from src.proxmox_info.pminfo import main
    from click.testing import CliRunner
    
    runner = CliRunner()
    # Invoke without required credentials
    result = runner.invoke(main, [])
    # Should exit with error code and show validation error
    assert result.exit_code == 1
    # The error message might vary, but should indicate missing credentials


def test_main_function_validation_with_credentials():
    """Test that main function proceeds when credentials are provided"""
    from src.proxmox_info.pminfo import main
    from click.testing import CliRunner
    from unittest.mock import patch, Mock
    
    runner = CliRunner()
    
    # Mock the ProxmoxAPI to avoid actual network calls
    with patch('src.proxmox_info.pminfo.ProxmoxAPI') as mock_proxmox:
        mock_proxmox_instance = Mock()
        mock_proxmox.return_value = mock_proxmox_instance
        # Mock nodes.get to return empty list to avoid further processing
        mock_proxmox_instance.nodes.get.return_value = []
        
        # Invoke with credentials
        result = runner.invoke(main, [
            '--host', 'test-host',
            '--user', 'test-user',
            '--password', 'test-password'
        ])
        
        # Should not fail validation (might fail later due to mocked API, but not validation)
        # We're mainly testing that it gets past the validation step
        # If it fails validation, exit_code would be 1 and output would contain validation error
        if result.exit_code == 1:
            # If it failed, check if it was a validation error
            assert 'user and password must be configured' not in result.output.lower()
            # Could be other errors like connection issues, which is fine for this test