#!/usr/bin/env python

import sys
from enum import Enum
from typing import Optional

import pandas
import rich.table
from proxmoxer import ProxmoxAPI
import proxmoxer.core
import pandas as pd
import humanize
import click
from rich.console import Console, Group
from rich.table import Table
from rich import box
from rich import inspect
from rich.tree import Tree
from rich.traceback import install
from dynaconf import ValidationError, Validator
from .config import settings
from ._version import __version__



pd.options.mode.copy_on_write = True
install(show_locals=True)

def machines_by_storage(current_node: proxmoxer.ProxmoxResource, current_storage: dict) -> pandas.DataFrame:
    """
    Finds all machines in a specified storage.

    :param current_node:  The current Proxmox node.
    :type current_node:  proxmoxer.ProxmoxResource
    :param current_storage: The current storage to inspect.
    :type current_storage: dict
    :return: The machines running on the specified storage.
    :rtype: dict
    """
    df = pd.DataFrame(current_node.storage(current_storage['storage']).content.get())
    return df[df['content'].isin(['images', 'rootdir'])]


def rejig_machines(machines: pandas.DataFrame) -> pandas.DataFrame:
    """
    This does a bunch of filtering and reorganising of machines to wittle down to the desired columns etc.

    :param machines: A Pandas DataFrame object
    :type machines: pandas.DataFrame
    :return: A Pandas DataFrame object
    :rtype: pandas.DataFrame
    """
    machines.drop(columns=['diskread', 'diskwrite', 'cpu', 'disk', 'swap', 'type'], errors='ignore', inplace=True)
    for k in ['maxdisk', 'maxmem', 'mem', 'netout', 'netin', 'maxswap']:
        try:
            machines[k] = machines[k].map(humanize.naturalsize)
        except KeyError:
            pass

    machines['uptime'] = machines['uptime'].map(humanize.naturaltime)
    machines['pid'] = machines['pid'].astype(int)
    machines.sort_index(axis=1, inplace=True)
    left_columns = ['name', 'vmid', 'status']
    new_columns = left_columns + [col for col in machines if col not in left_columns]
    machines = machines.reindex(columns=new_columns)

    return machines



def df_to_table(pandas_dataframe: pandas.DataFrame, rich_table: rich.table.Table, show_index: bool = True,
                index_name: Optional[str] = None, col_align_map: Optional[dict] = None) -> rich.table.Table:
    """
    Convert a pandas.DataFrame object into a rich.Table object.

    :param pandas_dataframe: A Pandas DataFrame to be converted to a rich Table.
    :type pandas_dataframe: pandas.DataFrame
    :param rich_table: A rich Table that should be populated by the DataFrame values.
    :type rich_table: rich.table.Table
    :param show_index: Add a column with a row count to the table. Defaults to True.
    :type show_index: bool
    :param index_name: The column name to give to the index column. Defaults to None, showing no value.
    :type index_name: str
    :param col_align_map: A map of columns describing alignment.
    :type col_align_map: dict
    :return:The rich Table instance passed, populated with the DataFrame values.
    :rtype: rich.table.Table
    """
    if show_index:
        index_name = str(index_name) if index_name else ""
        rich_table.add_column(index_name)

    for column in pandas_dataframe.columns:
        align = 'left'
        if col_align_map:
            try:
                align = col_align_map[column]
            except KeyError:
                pass
        rich_table.add_column(str(column), justify=align)

    for index, value_list in enumerate(pandas_dataframe.values.tolist()):
        row = [str(index)] if show_index else []
        row += [str(x) for x in value_list]
        rich_table.add_row(*row)

    return rich_table


class MachineType(Enum):
    VMs = 'Virtual machines'
    LXCs = "Linux containers"


@click.command()
@click.option('--host', '-h', help='The Proxmox hostname')
@click.option('--user', '-u', help='The Proxmox username')
@click.option('--password', '-p', help='The Proxmox password')
@click.option('--verify/--no-verify', default=True, help='Verify Proxmox certificate')
@click.option('--timeout', '-t', default=30, help='Timeout connecting to Proxmox')
@click.option('--storage', '-s', default='all', help='Filter by storage name')
@click.option('--output', '-o', default='basic', help='The output format: basic or tree')
@click.option('--filter', '-f', default='running', help='Status of machines to filter: running or all')
@click.option('--pager/--no-pager', '-l', default=False, help='Run the output through the system pager')
@click.version_option(version=__version__)
def main(host, user, password, verify, timeout, storage, output, filter, pager):
    validation_messages = {
        'must_exist_true': '{name} is required',
        'condition': '{name} is required',
    }

    # Register validators but dont trigger validation.
    settings.validators.register(
        Validator('host', 'user', 'password', must_exist=True, condition=lambda v: v is not None, messages=validation_messages),
        Validator('verify_ssl', is_type_of=bool),
        Validator('timeout', is_type_of=int),
    )

    try:
        settings.update({
            'host': host,
            'user': user,
            'password': password,
            'verify_ssl': verify,
            'timeout': timeout,
            'storage': storage,
            'output': output,
            'filter': filter,
        })
        settings.validators.validate()

    except ValidationError as e:
        print(e)
        sys.exit(1)

    proxmox = ProxmoxAPI(settings.host, user=settings.user, password=settings.password, verify_ssl=settings.verify_ssl,
                         timeout=settings.timeout)

    console = Console()

    col_align = {
        MachineType.VMs: {
            'vmid': 'right',
            'cpus': 'right',
            'maxdisk': 'right',
            'maxmem': 'right',
            'mem': 'right',
            'netout': 'right',
            'netin': 'right',
            'pid': 'right',
        },
        MachineType.LXCs: {
            'vmid': 'right',
            'cpus': 'right',
            'maxdisk': 'right',
            'maxmem': 'right',
            'maxswap': 'right',
            'mem': 'right',
            'netout': 'right',
            'netin': 'right',
            'pid': 'right',
        }
    }

    for node in proxmox.nodes.get():
        with console.status('Fetching info', spinner='dots10') as status:
            current_node = proxmox.nodes(node['node'])
            if output == 'basic':
                console.print(f'[bold green]Node: {node["node"]}')
                console.print()
            elif output == 'tree':
                tree = Tree(f'Node: {node["node"]}')

            for current_storage in current_node.storage.get(content='images,rootdir'):
                try:
                    status.update(f'Fetching storage: {current_storage["storage"]}')
                    if storage == 'all' or current_storage['storage'] == storage:
                        if output == 'basic':
                            console.rule(f'[green]Storage: {current_storage["storage"]}', align='left')
                        elif output == 'tree':
                            tree_storage = tree.add(f'[green]Storage: {current_storage["storage"]}')

                        machines = machines_by_storage(current_node, current_storage)
                        if machines.empty:
                            continue

                        for container_type in MachineType:
                            status.update(f'Fetching storage: {current_storage["storage"]} :right_arrow: {container_type.name}')
                            if container_type == MachineType.VMs:
                                df = pd.DataFrame(current_node.qemu.get())
                            elif container_type == MachineType.LXCs:
                                df = pd.DataFrame(current_node.lxc.get())
                            df = df[df['vmid'].isin(machines['vmid'])]

                            if not df.empty:
                                final_machines = rejig_machines(df[df['status'] == filter] if filter == 'running' else df)
                            else:
                                final_machines = pd.DataFrame()

                            if not final_machines.empty:
                                table = Table(title=container_type.value, show_header=True, header_style='on grey19',
                                              box=box.MINIMAL_HEAVY_HEAD, title_style='reverse')
                                table = df_to_table(final_machines, table, show_index=False, col_align_map=col_align[container_type])

                                if output == 'basic':
                                    console.print(f'\n[bright_yellow]:computer: {container_type.name}: {" ".join(str(x) for x in final_machines["vmid"].to_list())}')
                                    console.print(table)
                                elif output == 'tree':
                                    tree_storage.add(Group(f':computer: {container_type.name} :arrow_lower_right:', table))
                            else:
                                msg = f'[bright_yellow]No {container_type.name} found'
                                if output == 'basic':
                                    console.print(msg)
                                elif output == 'tree':
                                    tree_storage.add(Group(f':computer: {container_type.name} :arrow_lower_right:', msg))

                        if output == 'basic':
                            console.print()

                except proxmoxer.core.ResourceException:
                    print('Couldn\'t get datastores, moving on...')

    if output == 'tree':
        if pager:
            with console.pager():
                console.print(tree)
        else:
            console.print(tree)

if __name__ == '__main__':
    main()
