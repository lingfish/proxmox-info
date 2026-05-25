import pytest
from unittest.mock import Mock, MagicMock
import pandas as pd
from rich.console import Console


@pytest.fixture
def mock_proxmox():
    """Mock ProxmoxAPI object"""
    return Mock()


@pytest.fixture
def mock_node():
    """Mock node resource"""
    node = Mock()
    node.get.return_value = [{"node": "test-node"}]
    return node


@pytest.fixture
def mock_storage():
    """Mock storage resource"""
    storage = Mock()
    storage.get.return_value = [
        {"storage": "local", "content": "images,rootdir"},
        {"storage": "local-lvm", "content": "images"},
        {"storage": "iso", "content": "iso"}
    ]
    return storage


@pytest.fixture
def sample_lxc_data():
    """Sample LXC machine data"""
    return {
        'cpu': [0.00194461754596796, 0.00314130526656363, 0.00119668772059567],
        'cpus': [4, 4, 2],
        'disk': [0, 0, 0],
        'diskread': [0, 0, 0],
        'diskwrite': [0, 0, 0],
        'maxdisk': [34359738368, 42949672960, 16106127360],
        'maxmem': [2147483648, 4294967296, 1073741824],
        'mem': [1297941158, 1626994901, 354672108],
        'name': ['lxc_1', 'lxc_2', 'lxc_3'],
        'netin': [725478877942, 532929920, 2291167472],
        'netout': [1396481818572, 461004735, 1412958],
        'pid': [8285.0, 945130.0, 2682.0],
        'serial': [None, None, None],
        'status': ['running', 'running', 'running'],
        'tags': ['linux', None, 'linux'],
        'template': [None, None, None],
        'uptime': [3610802, 587726, 3610927],
        'vmid': [150, 132, 108]
    }


@pytest.fixture
def sample_vm_data():
    """Sample VM machine data"""
    return {
        'cpu': [0.01, 0.02],
        'cpus': [2, 4],
        'disk': [0, 0],
        'diskread': [0, 0],
        'diskwrite': [0, 0],
        'maxdisk': [53687091200, 107374182400],
        'maxmem': [8589934592, 17179869184],
        'mem': [4294967296, 8589934592],
        'name': ['vm_1', 'vm_2'],
        'netin': [1000000, 2000000],
        'netout': [2000000, 1000000],
        'pid': [1234.0, 5678.0],
        'serial': [None, None],
        'status': ['running', 'stopped'],
        'tags': [None, None],
        'template': [0, 0],
        'uptime': [3600, 0],
        'vmid': [101, 102],
        'vmstat': [{}, {}]
    }


@pytest.fixture
def empty_dataframe():
    """Empty pandas DataFrame"""
    return pd.DataFrame()


@pytest.fixture
def dataframe_with_nans():
    """DataFrame with NaN values in key columns"""
    return pd.DataFrame({
        'pid': [1.0, None, 3.0],
        'vmid': [100, None, 300],
        'cpus': [2.0, 4.0, None],
        'serial': [None, "some-serial", None],
        'template': [None, None, "template"],
        'maxdisk': [0, 1000, 0],
        'maxmem': [0, 0, 2000],
        'mem': [1000, 0, 0],
        'netin': [0, 0, 0],
        'netout': [0, 0, 0],
        'maxswap': [0, 0, 0],
        'uptime': [0, 3600, 0],
        'name': ['test1', 'test2', 'test3'],
        'status': ['running', 'stopped', 'running']
    })


@pytest.fixture
def dataframe_missing_columns():
    """DataFrame missing optional columns"""
    return pd.DataFrame({
        'vmid': [100, 200],
        'status': ['running', 'stopped'],
        'name': ['vm1', 'vm2'],
        'cpus': [2, 4],
        'maxdisk': [1000, 2000],
        'maxmem': [1000, 2000],
        'mem': [500, 1500]
    })


@pytest.fixture
def console():
    """Rich Console object"""
    return Console()