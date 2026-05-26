# proxmox-info — agent guide

## Build & test
- Build system: Hatch (hatchling + hatch-vcs). All commands via `hatch`.
- Run tests: `hatch test`
- Run coverage: `hatch test --cover`
- CI runs `hatch test --cover -- -v tests` across Python 3.9, 3.11 (GitLab CI, `.gitlab-ci.yml`)

## Package layout
- **src-layout**: `src/proxmox_info/` — package must have `__init__.py` for hatchling to properly discover it during editable install
- Entry point: `proxmox-info = "proxmox_info.pminfo:main"` (`[project.scripts]` in pyproject.toml)
- Tests in `tests/` (no package, just `__init__.py` marker)

## Known bugs (fix these first)
1. **`pminfo.py:57`** — `machines.sum(numeric_only=False)` concatenates string columns (`name`, `status`, `tags`) into garbage. Replace with numeric-only sum (was originally `['cpus', 'maxdisk', 'maxmem', 'mem', 'netin', 'netout']`).
2. **`pminfo.py:125-132`** — `df_to_table` declares `totals_dataframe: Optional[DataFrame]` but `rejig_machines` returns a `Series`. `.to_numpy().tolist()` on a Series returns a flat list, so `totals_list[-1][0] = 'Totals'` crashes with `TypeError: 'str' object does not support item assignment`.

## Test conventions
- **Runner**: `hatch test` (not plain pytest)
- **Fixtures**: shared in `tests/conftest.py` — `sample_lxc_data`, `sample_vm_data`, `dataframe_with_nans`, `dataframe_missing_columns`, `empty_dataframe`, `mock_node`, `mock_storage`, `mock_proxmox`, `console`
- **Mocking**: `unittest.mock.Mock`/`patch` or `mocker` (pytest-mock is installed)
- **CLI tests**: `click.testing.CliRunner`
- **Config tests**: require `FORCE_ENV_FOR_DYNACONF=testing` env var (set automatically by `hatch test`)
- **Import tests**: use `from src.proxmox_info.pminfo import ...` (package is editable-installed)

## Style
- Line length 120, single quotes (`[tool.ruff.format] quote-style = "single"`)
- Python >=3.9

## Dependencies
`proxmoxer`, `humanize`, `dynaconf`, `click`, `requests`, `pandas`, `rich`, `numpy`

## Project scope
CLI tool that reads Proxmox API per-node/per-storage and prints VM/container tables or trees. No persistent state, no database, no async.
