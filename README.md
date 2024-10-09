# proxmox-info

A CLI utility to return various info from the Proxmox API.

Currently, it only reports storage vs machines info.

## Table of contents

<!-- TOC -->
* [Proxmox-grapple](#proxmox-grapple)
  * [Table of contents](#table-of-contents)
  * [Purpose and uses](#purpose-and-uses)
    * [Running binaries](#running-binaries)
    * [Running things via a shell](#running-things-via-a-shell)
  * [Installation](#installation)
  * [Configuration](#configuration)
    * [Overview](#overview)
    * [Location](#location)
    * [Configuration dump](#configuration-dump)
    * [Configuration environments](#configuration-environments)
    * [Breaking change in 2.0.0](#breaking-change-in-200)
      * [Before 2.0.0 format](#before-200-format)
      * [New format](#new-format)
  * [Supported versions](#supported-versions)
<!-- TOC -->


## Purpose and uses

Ever needed to get a list of VMs or containers _per datastore_?

Why?  Perhaps you need to shutdown that storage for maintenance, upgrades etc., and need to move all running machines
off it (a la vSphere storage vMotion).

Then this is the tool for you.

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