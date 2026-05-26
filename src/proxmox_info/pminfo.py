#!/usr/bin/env python

import sys
from enum import Enum
from platform import machine
from typing import Optional, Union

import numpy as np
import pandas
import requests
import rich.table
from proxmoxer import ProxmoxAPI, AuthenticationError
import proxmoxer.core
import pandas as pd
import humanize
import click
from rich.console import Console, Group
from rich.status import Status
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


def machines_by_storage(current_node: proxmoxer.ProxmoxResource, current_storage: str) -> pandas.DataFrame:
    """Finds all machines in a specified storage."""

    content = current_node.storage(current_storage).content.get()
    df = pd.DataFrame(content)
    if df.empty:
        return df
    return df[df['content'].isin(['images', 'rootdir'])]


def rejig_machines(machines: pandas.DataFrame, human: bool) -> tuple[pandas.DataFrame, pandas.Series]:
    """This does a bunch of filtering and reorganising of machines to wittle down to the desired columns etc."""

    machines.drop(columns=['diskread', 'diskwrite', 'cpu', 'disk', 'swap', 'type'], errors='ignore', inplace=True)
    for k in ['pid', 'vmid', 'cpus']:
        if k in machines.columns:
            machines[k] = machines[k].fillna(0).astype('int')

    for k in ['serial', 'template']:
        if k in machines.columns:
            machines[k] = machines[k].fillna(0).astype(bool)

    # Compute totals for columns where sum is meaningful
    sum_columns = ['cpus', 'maxdisk', 'maxmem', 'mem', 'netout', 'netin', 'maxswap', 'uptime']
    existing_sum_columns = [col for col in sum_columns if col in machines.columns]
    totals = machines[existing_sum_columns].sum() if existing_sum_columns else pd.Series(dtype='float64')

    # vmid: count instead of sum
    if 'vmid' in machines.columns:
        totals['vmid'] = len(machines)

    # Convert to object dtype so humanized strings can be stored
    totals = totals.astype(object)

    if human:
        for k in ['maxdisk', 'maxmem', 'mem', 'netout', 'netin', 'maxswap']:
            if k in machines.columns:
                try:
                    machines[k] = machines[k].map(lambda x: 'N/A' if x == 0 else x)
                    machines[k] = machines[k].map(lambda x: humanize.naturalsize(x) if isinstance(x, (float, int)) else x)
                except (KeyError, TypeError, ValueError):
                    pass
            if k in totals.index:
                try:
                    totals[k] = humanize.naturalsize(totals[k])
                except (KeyError, TypeError, ValueError):
                    pass

        if 'uptime' in machines.columns:
            machines['uptime'] = machines['uptime'].map(humanize.naturaltime)
            machines.replace({'now': 'N/A'}, inplace=True)
        if 'uptime' in totals.index:
            try:
                totals['uptime'] = humanize.naturaldelta(totals['uptime'])
            except (KeyError, TypeError, ValueError):
                pass

    machines.sort_index(axis=1, inplace=True)
    left_columns = ['name', 'vmid', 'status']
    # Only include columns that actually exist in the DataFrame
    existing_left_columns = [col for col in left_columns if col in machines.columns]
    other_columns = [col for col in machines.columns if col not in left_columns]
    new_columns = existing_left_columns + other_columns
    machines = machines.reindex(columns=new_columns)

    return machines, totals


def df_to_table(pandas_dataframe: pandas.DataFrame,
                 rich_table: rich.table.Table,
                 totals_dataframe: Optional[Union[pandas.DataFrame, pandas.Series]] = None,
                 show_index: bool = True,
                 index_name: Optional[str] = None,
                 col_align_map: Optional[dict] = None
                 ) -> rich.table.Table:
    """Convert a pandas.DataFrame object into a rich.Table object."""

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

    # Convert DataFrame to list of lists, handling mixed types safely
    to_list = []
    for _, row in pandas_dataframe.iterrows():
        processed_row = []
        for val in row:
            if isinstance(val, (list, tuple, np.ndarray)):
                # Handle arrays/lists by converting to string representation
                processed_row.append(str(val))
            elif pd.isna(val):
                processed_row.append('')
            else:
                processed_row.append(str(val))
        to_list.append(processed_row)

    for index, value_list in enumerate(to_list):
        row = [str(index)] if show_index else []
        row += value_list  # Already converted to strings above
        rich_table.add_row(*row)

    if totals_dataframe is not None and not totals_dataframe.empty:
        if isinstance(totals_dataframe, pandas.Series):
            totals_dict = totals_dataframe.to_dict()
            totals_row = [str(totals_dict.get(col, '')) for col in pandas_dataframe.columns]
        else:
            totals_list = totals_dataframe.to_numpy(dtype=str, na_value='').tolist()
            totals_row = [str(x) for x in totals_list[0]] if totals_list else []
        if show_index:
            totals_row.insert(0, 'Totals')
        else:
            totals_row[0] = 'Totals'
        rich_table.add_section()
        rich_table.add_row(*totals_row)

    return rich_table


class MachineType(Enum):
    """Helper Enum"""

    VMs = 'Virtual machines'
    LXCs = "Linux containers"


def fetch_node_info(proxmox: ProxmoxAPI, node: proxmoxer.ProxmoxResource, console: Console) -> tuple[
    proxmoxer.ProxmoxResource, proxmoxer.ProxmoxResource, Status]:
    """Fetches node information."""

    with console.status("Fetching info", spinner="dots10") as status:
        current_node = proxmox.nodes(node["node"])
        yield node["node"], current_node, status


def fetch_storage_info(current_node: proxmoxer.ProxmoxResource, storage: str) -> str:
    """Fetches storage information."""
    for current_storage in current_node.storage.get(content="images,rootdir"):
        if storage == "all" or current_storage["storage"] == storage:
            yield current_storage["storage"]


@click.command()
@click.option('--host', '-h', default=settings.HOST, help='The Proxmox hostname')
@click.option('--user', '-u', default=settings.USER, help='The Proxmox username')
@click.option('--password', '-p', default=settings.PASSWORD, help='The Proxmox password')
@click.option('--verify/--no-verify', default=True, help='Verify Proxmox certificate')
@click.option('--timeout', '-t', default=30, help='Timeout connecting to Proxmox')
@click.option('--storage', '-s', default='all', help='Filter by storage name')
@click.option('--output', '-o', default='basic', help='The output format: basic or tree')
@click.option('--filter', '-f', default='running', help='Status of machines to filter: running, stopped or all')
@click.option('--pager/--no-pager', '-l', default=False, help='Run the output through the system pager')
@click.option('--human/--no-human', default=True, help='Show human-readable formatted output')
@click.version_option(version=__version__)
def main(host, user, password, verify, timeout, storage, output, filter, pager, human):
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
        if None in [user, password]:
            raise ValidationError('user and password must be configured.')

    except ValidationError as e:
        print(e)
        sys.exit(1)

    try:
        proxmox = ProxmoxAPI(settings.host, user=settings.user, password=settings.password, verify_ssl=settings.verify_ssl,
                             timeout=settings.timeout)
    except (proxmoxer.core.AuthenticationError, requests.exceptions.RequestException) as e:
        click.echo(e, err=True)
        sys.exit(1)

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
        for node_info, current_node, status in fetch_node_info(proxmox, node, console):
            if output == 'basic':
                console.print(f'[bold green]Node: {node_info}')
            elif output == 'tree':
                tree = Tree(f'Node: {node_info}')

            for current_storage in fetch_storage_info(current_node, storage):
                try:
                    status.update(f'Fetching storage: {current_storage}')
                    if output == 'basic':
                        console.rule(f'[green]Storage: {current_storage}', align='left')
                    elif output == 'tree':
                        tree_storage = tree.add(f'[green]Storage: {current_storage}')

                    machines = machines_by_storage(current_node, current_storage)
                    if machines.empty:
                        msg = f'[bright_yellow]Nothing applicable found'
                        if output == 'basic':
                            console.print(msg)
                        elif output == 'tree':
                            tree_storage.add(msg)
                        continue

                    for container_type in MachineType:
                        status.update(f'Fetching storage: {current_storage} :right_arrow: {container_type.name}')
                        if container_type == MachineType.VMs:
                            df = pd.DataFrame(current_node.qemu.get())
                        elif container_type == MachineType.LXCs:
                            df = pd.DataFrame(current_node.lxc.get())
                        df = df[df['vmid'].isin(machines['vmid'])]

                        if not df.empty:
                            final_machines, totals = rejig_machines(df[df['status'] == filter] if filter in ['stopped', 'running'] else df, human)
                        else:
                            final_machines, totals = pd.DataFrame()

                        if not final_machines.empty:
                            table = Table(title=container_type.value, show_header=True, header_style='on grey19',
                                          box=box.MINIMAL_HEAVY_HEAD, title_style='reverse')
                            table = df_to_table(pandas_dataframe=final_machines, rich_table=table,
                                                totals_dataframe=totals, show_index=False,
                                                col_align_map=col_align[container_type])

                            if output == 'basic':
                                console.print(
                                    f'\n[bright_yellow]:computer: {container_type.name}: {" ".join(str(x) for x in final_machines["vmid"].to_list())}')
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
