import pandas as pd
import pytest
from pandas import DataFrame, Series

from src.proxmox_info.pminfo import rejig_machines


@pytest.fixture
def lxc_machines():
    return {'cpu': [0.00194461754596796, 0.00314130526656363, 0.00119668772059567], 'cpus': [4, 4, 2],
            'disk': [0, 0, 0], 'diskread': [0, 0, 0], 'diskwrite': [0, 0, 0],
            'maxdisk': [34359738368, 42949672960, 16106127360],
            'maxmem': [2147483648, 4294967296, 1073741824], 'mem': [1297941158, 1626994901, 354672108],
            'name': ['lxc_1', 'lxc_2', 'lxc_3'], 'netin': [725478877942, 532929920, 2291167472],
            'netout': [1396481818572, 461004735, 1412958], 'pid': [8285.0, 945130.0, 2682.0],
            'serial': [None, None, None], 'status': ['running', 'running', 'running'],
            'tags': ['linux', None, 'linux'], 'template': [None, None, None],
            'uptime': [3610802, 587726, 3610927], 'vmid': [150, 132, 108]}

def test_rejig_machines(lxc_machines):
    df, totals = rejig_machines(DataFrame(lxc_machines), human=False)
    assert isinstance(df, DataFrame)
    assert isinstance(totals, Series)

    assert not set(df.columns).issubset({'diskread', 'diskwrite', 'cpu', 'disk', 'swap', 'type'})

    df, totals = rejig_machines(DataFrame(lxc_machines), human=True)
    assert isinstance(totals, Series)
    assert df['maxdisk'][0] == '34.4 GB'
    assert df['maxmem'][0] == '2.1 GB'
    assert df['mem'][0] == '1.3 GB'
    assert df['netout'][0] == '1.4 TB'
    assert df['netin'][0] == '725.5 GB'

    df, _ = rejig_machines(DataFrame(lxc_machines), human=True)
    assert list(df.columns)[:3] == ['name', 'vmid', 'status']
