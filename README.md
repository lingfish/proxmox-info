# proxmox-info

[![PyPI - Version](https://img.shields.io/pypi/v/proxmox-info.svg)](https://pypi.org/project/proxmox-info/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/proxmox-info.svg)](https://pypi.org/project/proxmox-info/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

A CLI utility to return various info from the Proxmox API.

Currently, it only reports storage vs machines info.

## Table of contents

<!-- TOC -->
* [proxmox-info](#proxmox-info)
  * [Table of contents](#table-of-contents)
  * [Features](#features)
  * [Purpose and uses](#purpose-and-uses)
  * [Screenshots](#screenshots)
  * [Installation](#installation)
  * [Configuration](#configuration)
    * [Overview](#overview)
    * [Location](#location)
  * [Supported versions](#supported-versions)
<!-- TOC -->

## Features

- **Per-datastore VM/container listing** — see which QEMU VMs and LXC containers live on each storage volume
- **Two output modes** — clean table view or hierarchical tree view
- **Multiple node support** — aggregates across all Proxmox nodes in your cluster
- **Status filtering** — show only running machines, stopped machines, or all
- **Human-readable output** — automatic formatting of sizes and uptimes via `--human`
- **Pager support** — pipe through your system pager with `--pager`
- **Config file or CLI args** — YAML config with Dynaconf, or override everything on the command line

## Purpose and uses

Ever needed to get a list of VMs or containers _per datastore_?

Why?  Perhaps you need to shutdown that storage for maintenance, upgrades etc., and need to move all running machines
off it (a la vSphere storage vMotion).

Then this is the tool for you.

## Screenshots

Default table view — VMs and containers listed per datastore with status, CPU, memory, disk, and network columns:

![Default table view showing VMs grouped by storage](https://raw.githubusercontent.com/lingfish/proxmox-info/refs/heads/main/docs/default%20screen.png)

Tree view — hierarchical display of node > storage > machine type > machine details:

![Tree view showing node hierarchy](https://raw.githubusercontent.com/lingfish/proxmox-info/refs/heads/main/docs/tree%20view.png)

## Installation

The recommended way to install `proxmox-info` is to use [pipx](https://pipx.pypa.io/stable/).

After getting `pipx` installed, simply run:

```shell
username@proxmox:~$ pipx install proxmox-info
```

Please [don't use pip system-wide](https://docs.python.org/3.11/installing/index.html#installing-into-the-system-python-on-linux).

You can of course also install it using classic virtualenvs.

## Configuration

### Overview

`proxmox-info` is configured with a YAML-style file.  An example:

```yaml
host: zzz
user: zap
password: some_password
```

### Location

The default location for the configuration is `/etc/proxmox_info.yml`, or `proxmox_info.yml` in the current
working directory, but this can also be specified on the commandline.

If a non-absolute path is given, Dynaconf will iterate upwards: it will look at each parent up to the root of the
system. For each visited folder, it will also try looking inside a `/config` folder.

## Supported versions

`proxmox-info` supports the following VE versions:

| VE version | Debian version | Python version | VE EoL  |
|------------|----------------|----------------|---------|
| 8          | 12 (Bookworm)  | 3.11           | TBA     |
| 7          | 11 (Bullseye)  | 3.9            | 2024-07 |
