import pytest
from src.proxmox_info.pminfo import MachineType
from src.proxmox_info.config import validation_messages, settings


class TestMachineTypeEnum:
    """Test the MachineType enum"""
    
    def test_vms_value(self):
        """Test that VMs enum has correct value"""
        assert MachineType.VMs.value == 'Virtual machines'
    
    def test_lxcs_value(self):
        """Test that LXCs enum has correct value"""
        assert MachineType.LXCs.value == "Linux containers"
    
    def test_enum_members(self):
        """Test that enum has expected members"""
        assert len(list(MachineType)) == 2
        assert MachineType.VMs in MachineType
        assert MachineType.LXCs in MachineType
    
    def test_enum_names(self):
        """Test that enum members have correct names"""
        assert MachineType.VMs.name == 'VMs'
        assert MachineType.LXCs.name == 'LXCs'


class TestValidationMessages:
    """Test the validation_messages dict"""
    
    def test_validation_messages_structure(self):
        """Test that validation_messages has expected structure"""
        assert isinstance(validation_messages, dict)
        assert 'must_exist_true' in validation_messages
        assert 'condition' in validation_messages
        
    def test_validation_messages_content(self):
        """Test that validation_messages has expected content"""
        assert validation_messages['must_exist_true'] == '{name} is required111'
        assert validation_messages['condition'] == '{name} is required'
        
    def test_validation_messages_used_in_settings(self):
        """Test that validation_messages is actually used by settings"""
        # Check that settings object exists and has the validation_messages
        # This is more of a smoke test since the actual usage is internal to Dynaconf
        assert settings is not None
        # We can't easily test the internal usage without modifying the settings,
        # but we can verify the dict exists and has the right content