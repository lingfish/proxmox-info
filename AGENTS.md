# proxmox-info — agent guide

## Build & test
- Build system: Hatch (hatchling + hatch-vcs). All commands via `hatch`.
- Run tests: `hatch test`
- Run coverage: `hatch test --cover`
- CI runs `hatch test --cover -- -v tests` across Python 3.9, 3.11 (GitLab CI, `.gitlab-ci.yml`)

## Package layout
- **src-layout**: `src/proxmox_info/` — must have `__init__.py` for hatchling to discover it during editable install
- Entry point: `proxmox-info = "proxmox_info.pminfo:main"` (`[project.scripts]` in pyproject.toml)
- Tests in `tests/` (no package, just `__init__.py` marker)
- Tests import from `src.proxmox_info.pminfo` (editable-installed, `src/` on path)

## Test conventions
- **Runner**: `hatch test` (not plain `pytest`)
- **Fixtures**: shared in `tests/conftest.py`
- **Mocking**: `unittest.mock.Mock`/`patch` or `mocker` (pytest-mock installed)
- **CLI tests**: `click.testing.CliRunner`
- **Config tests**: require `FORCE_ENV_FOR_DYNACONF=testing` env var (set automatically by `hatch test`)
- **Test count**: 54 tests across 4 files (`test_pminfo.py:33`, `test_main.py:7`, `test_validation.py:7`, `test_enum_and_config.py:7`)

## Code quirks
- `pandas` imported as both `import pandas` and `import pandas as pd` in pminfo.py — use `pd` alias in tests
- `numpy` imported as `np`; used for NaN handling in `df_to_table`
- `MachineType` enum at `pminfo.py:141` (`VMs`, `LXCs`)
- `df_to_table` accepts `totals_dataframe: Optional[Union[DataFrame, Series]]` — runtime type from `rejig_machines` is `Series`
- Two output modes: `basic` (flat tables) and `tree` (hierarchical via `rich.tree.Tree`)

## Style
- Line length 120, single quotes (`[tool.ruff.format] quote-style = "single"`)
- Python >=3.9

## Dependencies
`proxmoxer`, `humanize`, `dynaconf`, `click`, `requests`, `pandas`, `rich`, `numpy`

## Project scope
CLI tool that reads Proxmox API per-node/per-storage and prints VM/container tables or trees. No persistent state, no database, no async.
