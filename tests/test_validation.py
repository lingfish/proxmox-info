from dynaconf import Dynaconf, Validator, ValidationError
import pytest


@pytest.mark.skip()
def test_update():
    settings = Dynaconf(
        settings_files=['proxmox_info.yml'],
        # apply_default_on_none=True,
        core_loaders=['YAML'],
        validate_on_update=False,
        validators=[
            Validator('host', 'user', 'password', must_exist=True),

            Validator('verify_ssl', is_type_of=bool),
            Validator('timeout', is_type_of=int),
        ]
    )

    settings.update({'host': 'blah'})
    settings.host

@pytest.mark.skip()
def test_update_2():
    settings = Dynaconf(
        settings_files=['proxmox_info.yml'],
        # apply_default_on_none=True,
        core_loaders=['YAML'],
        validate_on_update=True,
        # validators=[
        #     Validator('host', 'user', 'password', must_exist=True),
        #
        #     Validator('verify_ssl', is_type_of=bool),
        #     Validator('timeout', is_type_of=int),
        # ]
    )

    # Register validators but dont trigger validation.
    settings.validators.register(
        Validator('host', 'user', 'password', must_exist=True, condition=lambda v: v is not None),
        Validator('verify_ssl', is_type_of=bool),
        Validator('timeout', is_type_of=int),
    )

    settings.update({
        'host': None,
        'user': None,
        'password': None,
    })
    with pytest.raises(ValidationError):
        settings.host
