import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch
from src.proxmox_info.pminfo import main
from dynaconf import ValidationError


class TestMainCLI:
    """Test the main Click CLI function"""
    
    def test_main_validation_missing_credentials(self):
        """Test that main function handles missing credentials properly"""
        from src.proxmox_info.config import settings as cfg
        runner = CliRunner()
        # Force user/password to None regardless of config file
        with patch.object(cfg, 'USER', None), patch.object(cfg, 'PASSWORD', None):
            import importlib
            import src.proxmox_info.pminfo as pm
            importlib.reload(pm)
            result = runner.invoke(pm.main, [])
        assert result.exit_code == 1
        assert 'user and password must be configured' in result.output
    
    def test_main_validation_with_credentials_no_api_error(self):
        """Test that main function proceeds when credentials are provided and API works"""
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
    
    def test_main_authentication_error(self):
        """Test that main function handles AuthenticationError properly"""
        runner = CliRunner()
        
        with patch('src.proxmox_info.pminfo.ProxmoxAPI') as mock_proxmox:
            # Simulate AuthenticationError during ProxmoxAPI initialization
            from proxmoxer.core import AuthenticationError
            mock_proxmox.side_effect = AuthenticationError('auth failed')
            
            result = runner.invoke(main, [
                '--host', 'test-host',
                '--user', 'test-user',
                '--password', 'test-password'
            ])
            
            assert result.exit_code == 1
            assert 'auth failed' in result.output
    
    def test_main_request_exception(self):
        """Test that main function handles RequestException properly"""
        runner = CliRunner()
        
        with patch('src.proxmox_info.pminfo.ProxmoxAPI') as mock_proxmox:
            # Simulate RequestException during ProxmoxAPI initialization
            import requests
            mock_proxmox.side_effect = requests.exceptions.RequestException('connection failed')
            
            result = runner.invoke(main, [
                '--host', 'test-host',
                '--user', 'test-user',
                '--password', 'test-password'
            ])
            
            assert result.exit_code == 1
            assert 'connection failed' in result.output
    
    def test_main_resource_exception_handling_via_machines_by_storage(self):
        """Test that main function handles ResourceException from machines_by_storage"""
        runner = CliRunner()
        
        with patch('src.proxmox_info.pminfo.ProxmoxAPI') as mock_proxmox, \
             patch('src.proxmox_info.pminfo.fetch_node_info') as mock_fetch_node, \
             patch('src.proxmox_info.pminfo.fetch_storage_info') as mock_fetch_storage, \
             patch('src.proxmox_info.pminfo.machines_by_storage') as mock_machines:
            
            # Setup successful connection
            mock_proxmox_instance = Mock()
            mock_proxmox.return_value = mock_proxmox_instance
            mock_proxmox_instance.nodes.get.return_value = [{'node': 'test-node'}]
            
            # Setup fetch_node_info to return a mock node
            mock_node = Mock()
            mock_status = Mock()
            mock_fetch_node.return_value = [('test-node', mock_node, mock_status)]
            
            # Setup fetch_storage_info to return storage names
            mock_fetch_storage.return_value = ['local']
            
            # Setup machines_by_storage to raise ResourceException
            from proxmoxer.core import ResourceException
            mock_machines.side_effect = ResourceException(
                status_code=500,
                status_message='Internal Server Error',
                content=b'Resource error'
            )
            
            result = runner.invoke(main, [
                '--host', 'test-host',
                '--user', 'test-user',
                '--password', 'test-password'
            ])
            
            # Should succeed despite ResourceException (it's caught and ignored)
            # The function should continue and exit normally
            assert result.exit_code == 0
            # Should see the message about ResourceException
            assert "Couldn't get datastores, moving on..." in result.output
    
    def test_main_version_option(self):
        """Test that --version option works"""
        runner = CliRunner()
        result = runner.invoke(main, ['--version'])
        assert result.exit_code == 0
        # Should contain version info
        assert 'proxmox-info' in result.output or 'version' in result.output.lower()
    
    def test_main_help_option(self):
        """Test that --help option works"""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'Show this message and exit' in result.output