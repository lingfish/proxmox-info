from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    settings_files=['proxmox_info.yml'],
    environments=False,
    apply_default_on_none=True,
    core_loaders=['YAML'],
    validators=[
        Validator('host', 'user', 'password', must_exist=True),

        Validator('verify_ssl', is_type_of=bool),
        Validator('timeout', is_type_of=int),
    ]
)