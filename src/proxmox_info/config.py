from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    settings_files=['proxmox_info.yml'],
    # apply_default_on_none=True,
    core_loaders=['YAML'],
    validate_on_update=True,
)