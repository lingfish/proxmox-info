from dynaconf import Dynaconf, Validator

validation_messages = {
    'must_exist_true': '{name} is required111',
    'condition': '{name} is required',
}

settings = Dynaconf(
    settings_files=['proxmox_info.yml'],
    apply_default_on_none=True,
    core_loaders=['YAML'],
    validate_on_update=False,
    validators=[
        Validator('host', default='localhost'),
        Validator('user', 'password', default=None),
        Validator('verify_ssl', is_type_of=bool),
        Validator('timeout', is_type_of=int),
    ],
)