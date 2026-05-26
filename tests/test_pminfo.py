import pandas as pd
import pytest
from pandas import DataFrame, Series
from unittest.mock import Mock, patch
from rich.table import Table

from src.proxmox_info.pminfo import (
    rejig_machines,
    df_to_table,
    machines_by_storage,
    fetch_node_info,
    fetch_storage_info,
    MachineType
)


class TestRejigMachines:
    """Test the rejig_machines function"""
    
    def test_empty_dataframe(self, empty_dataframe):
        """Test with completely empty DataFrame"""
        df, totals = rejig_machines(empty_dataframe, human=False)
        assert isinstance(df, DataFrame)
        assert isinstance(totals, Series)
        assert df.empty
        assert totals.empty
    
    def test_missing_columns(self, dataframe_missing_columns):
        """Test DataFrame missing optional columns"""
        df, totals = rejig_machines(dataframe_missing_columns, human=False)
        # Should not crash and should return DataFrame
        assert isinstance(df, DataFrame)
        assert isinstance(totals, Series)
        # Original columns should still be there
        assert 'vmid' in df.columns
        assert 'status' in df.columns
        assert 'name' in df.columns
    
    def test_nan_handling(self, dataframe_with_nans):
        """Test handling of NaN values in key columns"""
        df, totals = rejig_machines(dataframe_with_nans, human=False)
        # NaN in pid, vmid, cpus should become 0
        assert df['pid'].iloc[1] == 0
        assert df['vmid'].iloc[1] == 0
        assert df['cpus'].iloc[2] == 0
        # None in serial, template should become False (0 then astype(bool))
        assert df['serial'].iloc[0] == False
        assert df['serial'].iloc[1] == True  # "some-serial" is truthy
        assert df['template'].iloc[2] == True
    
    def test_zero_sizes_human_mode(self, dataframe_with_nans):
        """Test zero sizes become 'N/A' in human mode"""
        df, totals = rejig_machines(dataframe_with_nans, human=True)
        # Zero values should become 'N/A'
        assert df['maxdisk'].iloc[0] == 'N/A'
        assert df['maxmem'].iloc[0] == 'N/A'
        assert df['mem'].iloc[1] == 'N/A'
        assert df['netin'].iloc[0] == 'N/A'
        assert df['netout'].iloc[0] == 'N/A'
        assert df['maxswap'].iloc[0] == 'N/A'
        # Zero uptime should become 'N/A'
        assert df['uptime'].iloc[0] == 'N/A'
        assert df['uptime'].iloc[2] == 'N/A'
        # Non-zero values should be humanized
        assert df['maxdisk'].iloc[1] != 'N/A'  # 1000 bytes
        assert df['maxmem'].iloc[2] != 'N/A'  # 2000 bytes
    
    def test_column_ordering(self, sample_lxc_data):
        """Test that name, vmid, status are first columns"""
        df, totals = rejig_machines(DataFrame(sample_lxc_data), human=False)
        assert list(df.columns)[:3] == ['name', 'vmid', 'status']
    
    def test_totals_series(self, sample_lxc_data):
        """Test that totals Series is returned correctly"""
        df, totals = rejig_machines(DataFrame(sample_lxc_data), human=False)
        assert isinstance(totals, Series)
        # Should have sums for meaningful numeric columns
        assert 'cpus' in totals.index
        assert 'maxdisk' in totals.index
        assert 'maxmem' in totals.index
        # vmid should be count, not sum
        assert totals['vmid'] == 3  # count of 3 machines
        # uptime should be sum of seconds
        assert totals['uptime'] == 7809455  # 3610802+587726+3610927
        # pid should NOT be in totals (meaningless to sum)
        assert 'pid' not in totals.index

    def test_totals_excludes_string_columns(self, sample_lxc_data):
        """Test that totals does not contain concatenated string columns"""
        _, totals = rejig_machines(DataFrame(sample_lxc_data), human=False)
        assert 'name' not in totals.index
        assert 'status' not in totals.index
        assert 'tags' not in totals.index
    
    def test_totals_human(self, sample_lxc_data):
        """Test totals are humanized when human=True"""
        _, totals = rejig_machines(DataFrame(sample_lxc_data), human=True)
        # Byte-size totals should be humanized strings
        assert isinstance(totals['maxdisk'], str)
        assert isinstance(totals['maxmem'], str)
        assert isinstance(totals['mem'], str)
        # vmid should still be a count (int)
        assert totals['vmid'] == 3
        # uptime should be humanized as duration (e.g. "3 months", "90 days")
        assert isinstance(totals['uptime'], str)
        assert totals['uptime'] != str(7809455)  # not raw seconds

    def test_human_vs_non_human_mode(self, sample_lxc_data):
        """Test difference between human and non-human mode"""
        df_nonhuman, _ = rejig_machines(DataFrame(sample_lxc_data), human=False)
        df_human, _ = rejig_machines(DataFrame(sample_lxc_data), human=True)
        
        # Non-human mode should have numeric values (numpy types are OK)
        assert pd.api.types.is_numeric_dtype(df_nonhuman['maxdisk'])
        assert pd.api.types.is_numeric_dtype(df_nonhuman['mem'])
        
        # Human mode should have string values (humanized or 'N/A')
        assert isinstance(df_human['maxdisk'].iloc[0], str)
        assert isinstance(df_human['mem'].iloc[0], str)
        
        # Specific known conversions from original test
        assert df_human['maxdisk'][0] == '34.4 GB'
        assert df_human['maxmem'][0] == '2.1 GB'
        assert df_human['mem'][0] == '1.3 GB'
        assert df_human['netout'][0] == '1.4 TB'
        assert df_human['netin'][0] == '725.5 GB'


class TestDfToTable:
    """Test the df_to_table function"""
    
    def test_basic_conversion(self):
        """Test basic DataFrame to table conversion"""
        df = DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        table = df_to_table(df, Table())
        # By default, show_index=True, so we get index column + data columns
        assert len(table.columns) == 3  # index col + col1 + col2
        assert len(table.rows) == 2
    
    def test_with_index_true(self):
        """Test with show_index=True (default)"""
        df = DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        table = df_to_table(df, Table(), show_index=True)
        # Should have index column + data columns
        assert len(table.columns) == 3
        # First column should be the index
        assert table.columns[0].header == ""
    
    def test_with_custom_index_name(self):
        """Test with custom index_name"""
        df = DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        table = df_to_table(df, Table(), show_index=True, index_name="Row")
        assert table.columns[0].header == "Row"
    
    def test_without_index(self):
        """Test with show_index=False"""
        df = DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        table = df_to_table(df, Table(), show_index=False)
        # Should only have data columns
        assert len(table.columns) == 2
    
    def test_with_totals_dataframe(self):
        """Test with non-empty totals DataFrame"""
        df = DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        totals = DataFrame({'col1': [3], 'col2': [7]})  # Sums
        table = df_to_table(df, Table(), totals_dataframe=totals)
        # to_list[:-1] excludes last data row, so 1 data + 1 section + 1 totals = 3 rows
        assert len(table.rows) == 3  # 1 data + 1 section + 1 totals
    
    def test_with_totals_series(self):
        """Test with non-empty totals Series (runtime type from rejig_machines)"""
        df = DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        totals = Series({'col1': 3, 'col2': 7})
        table = df_to_table(df, Table(), totals_dataframe=totals)
        assert len(table.rows) == 3  # 2 data + 1 section + 1 totals

    def test_with_totals_series_show_index_false(self):
        """Test with totals Series and show_index=False"""
        df = DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        totals = Series({'col1': 3, 'col2': 7})
        table = df_to_table(df, Table(), totals_dataframe=totals, show_index=False)
        assert len(table.rows) == 3  # 2 data + 1 section + 1 totals

    def test_with_empty_totals_dataframe(self):
        """Test with empty totals DataFrame (should not add section)"""
        df = DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        totals = DataFrame()  # Empty
        table = df_to_table(df, Table(), totals_dataframe=totals)
        # Should only have data rows
        assert len(table.rows) == 2
    
    def test_with_none_totals(self):
        """Test with None totals DataFrame"""
        df = DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        table = df_to_table(df, Table(), totals_dataframe=None)
        # Should only have data rows
        assert len(table.rows) == 2
    
    def test_column_alignment(self):
        """Test col_align_map parameter"""
        df = DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        col_align_map = {'col1': 'right', 'col2': 'center'}
        table = df_to_table(df, Table(), col_align_map=col_align_map)
        assert table.columns[1].justify == 'right'
        assert table.columns[2].justify == 'center'
    
    def test_column_alignment_default(self):
        """Test default alignment when map doesn't contain column"""
        df = DataFrame({'col1': [1, 2], 'col2': ['a', 'b'], 'col3': [3.0, 4.0]})
        col_align_map = {'col1': 'right'}  # Only specify for col1
        table = df_to_table(df, Table(), col_align_map=col_align_map)
        # With show_index=True (default), first column is the index column (left-aligned)
        # Second column is 'col1' which should be right-aligned (specified)
        # Third column is 'col2' which should be left-aligned (default)
        assert table.columns[0].justify == 'left'   # Index column
        assert table.columns[1].justify == 'right'  # Specified
        assert table.columns[2].justify == 'left'   # Default
    
    def test_empty_dataframe(self):
        """Test with completely empty DataFrame"""
        df = DataFrame()
        table = df_to_table(df, Table())
        # By default, show_index=True, so we get index column even with empty DF
        assert len(table.columns) == 1  # index column only
        assert len(table.rows) == 0
    
    def test_mixed_data_types(self):
        """Test handling of mixed data types"""
        df = DataFrame({
            'str_col': ['hello', 'world'],
            'int_col': [1, 2],
            'float_col': [1.5, 2.5],
            'none_col': [None, None],
            'list_col': ['[1, 2]', '[3, 4]']  # Pre-convert to string to avoid issues
        })
        table = df_to_table(df, Table())
        # Should not crash and should convert everything to strings
        # By default, show_index=True, so we get index column + data columns
        assert len(table.columns) == 6  # index col + 5 data columns
        assert len(table.rows) == 2
    
    def test_nan_values(self):
        """Test handling of NaN values"""
        df = DataFrame({
            'col1': [1, None, 3],
            'col2': [None, 2, None]
        })
        table = df_to_table(df, Table())
        assert len(table.rows) == 3


class TestMachinesByStorage:
    """Test the machines_by_storage function"""
    
    def test_normal_case(self, mock_storage):
        """Test normal case with images/rootdir content"""
        # We need to mock the storage chain: current_node.storage('local').content.get()
        # Create a mock for the specific storage resource
        mock_specific_storage = Mock()
        mock_specific_storage.content.get.return_value = [
            {'content': 'images', 'volid': 'local:100/vm-100-disk-0.qcow2'},
            {'content': 'rootdir', 'volid': 'local:101/rootdir'},
            {'content': 'iso', 'volid': 'local:iso/ubuntu.iso'}  # Should be filtered out
        ]
        
        # Configure the mock_storage to return our specific storage when called with 'local'
        mock_storage.storage.return_value = mock_specific_storage
        
        result = machines_by_storage(mock_storage, 'local')
        assert isinstance(result, DataFrame)
        assert len(result) == 2  # Only images and rootdir
        assert all(result['content'].isin(['images', 'rootdir']))
    
    def test_empty_response(self, mock_storage):
        """Test when storage returns empty list"""
        mock_specific_storage = Mock()
        mock_specific_storage.content.get.return_value = []
        mock_storage.storage.return_value = mock_specific_storage
        
        result = machines_by_storage(mock_storage, 'local')
        assert isinstance(result, DataFrame)
        assert result.empty
    
    def test_no_matching_content(self, mock_storage):
        """Test when no content matches images/rootdir"""
        mock_specific_storage = Mock()
        mock_specific_storage.content.get.return_value = [
            {'content': 'iso', 'volid': 'local:iso/ubuntu.iso'},
            {'content': 'snapshot', 'volid': 'local:snapshot/test'}
        ]
        mock_storage.storage.return_value = mock_specific_storage
        
        result = machines_by_storage(mock_storage, 'local')
        assert isinstance(result, DataFrame)
        assert result.empty
    
    def test_mixed_content(self, mock_storage):
        """Test mix of matching and non-matching content"""
        mock_specific_storage = Mock()
        mock_specific_storage.content.get.return_value = [
            {'content': 'images', 'volid': 'local:100/vm-100-disk-0.qcow2'},
            {'content': 'rootdir', 'volid': 'local:101/rootdir'},
            {'content': 'iso', 'volid': 'local:iso/ubuntu.iso'},
            {'content': 'snapshot', 'volid': 'local:snapshot/test'}
        ]
        mock_storage.storage.return_value = mock_specific_storage
        
        result = machines_by_storage(mock_storage, 'local')
        assert isinstance(result, DataFrame)
        assert len(result) == 2  # Only images and rootdir
        assert all(result['content'].isin(['images', 'rootdir']))


class TestFetchNodeInfo:
    """Test the fetch_node_info function"""
    
    def test_generator_yields_correct_tuple(self, mock_proxmox, mock_node, console):
        """Test that generator yields exactly one tuple with correct contents"""
        # Setup mocks
        mock_proxmox.nodes.return_value.get.return_value = [{'node': 'test-node'}]
        mock_proxmox.nodes.return_value = mock_node
        
        # Call the generator
        gen = fetch_node_info(mock_proxmox, {'node': 'test-node'}, console)
        result = list(gen)  # Exhaust the generator
        
        # Should yield exactly one item
        assert len(result) == 1
        node_name, current_node, status = result[0]
        
        # Check contents
        assert node_name == 'test-node'
        assert current_node == mock_node
        # Status should be a Status object from rich
        from rich.status import Status
        assert isinstance(status, Status)
    
    def test_console_status_called(self, mock_proxmox, mock_node, console):
        """Test that console.status is called with correct parameters"""
        mock_proxmox.nodes.return_value.get.return_value = [{'node': 'test-node'}]
        mock_proxmox.nodes.return_value = mock_node
        
        # Mock the status context manager
        with patch.object(console, 'status') as mock_status:
            mock_status.return_value.__enter__.return_value = Mock()
            
            gen = fetch_node_info(mock_proxmox, {'node': 'test-node'}, console)
            list(gen)  # Exhaust generator
            
            # Verify console.status was called
            mock_status.assert_called_once_with("Fetching info", spinner="dots10")


class TestFetchStorageInfo:
    """Test the fetch_storage_info function"""
    
    def test_all_storages(self, mock_node):
        """Test when storage='all' yields all storages"""
        # The API call already filters by content=images,rootdir server-side
        # The function just matches storage names
        mock_node.storage.get.return_value = [
            {"storage": "local"},
            {"storage": "local-lvm"},
            {"storage": "iso"},
        ]
        gen = fetch_storage_info(mock_node, 'all')
        result = list(gen)
        assert len(result) == 3
        assert 'local' in result
        assert 'local-lvm' in result
        assert 'iso' in result
    
    def test_specific_storage_match(self, mock_node):
        """Test when storage matches exactly"""
        mock_node.storage.get.return_value = [
            {"storage": "local", "content": "images,rootdir"},
            {"storage": "local-lvm", "content": "images"}
        ]
        gen = fetch_storage_info(mock_node, 'local')
        result = list(gen)
        assert len(result) == 1
        assert result[0] == 'local'
    
    def test_specific_storage_no_match(self, mock_node):
        """Test when storage doesn't match any"""
        mock_node.storage.get.return_value = [
            {"storage": "local", "content": "images,rootdir"},
            {"storage": "local-lvm", "content": "images"}
        ]
        gen = fetch_storage_info(mock_node, 'nonexistent')
        result = list(gen)
        assert len(result) == 0
    
    def test_content_filter(self, mock_node):
        """Test that storage.get is called with content='images,rootdir'"""
        mock_node.storage.get.return_value = []
        list(fetch_storage_info(mock_node, 'all'))  # Consume the generator to trigger the call
        mock_node.storage.get.assert_called_once_with(content="images,rootdir")
    
    def test_empty_response(self, mock_node):
        """Test when storage.get returns empty list"""
        mock_node.storage.get.return_value = []
        gen = fetch_storage_info(mock_node, 'all')
        result = list(gen)
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__])