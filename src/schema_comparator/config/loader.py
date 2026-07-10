"""Load and validate connection profiles from a local YAML config file.

Phase 4 adds fail-fast gates: missing file and malformed/wrong-shape YAML.
Trim/duplicate/validation are added in Phase 5.
"""

import os

import yaml

from schema_comparator.config.errors import ConfigFileNotFoundError, ConfigParseError
from schema_comparator.config.models import ConnectionProfile


def load_profiles(config_path: str | os.PathLike[str]) -> list[ConnectionProfile]:
    """Load connection profiles from the YAML file at `config_path`.

    `config_path` is a required positional parameter with no default: the
    loader performs no implicit path resolution (no cwd/repo-root default,
    no environment-variable-derived path). Omitting it raises the natural
    `TypeError` from Python's argument binding.
    """
    if not os.path.exists(config_path):
        raise ConfigFileNotFoundError.at_path(str(config_path))

    with open(config_path, encoding="utf-8") as handle:
        try:
            document = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            # Never embed str(exc): PyYAML error text can echo a snippet of
            # the offending line/connection-string fragment. Chain `from
            # exc` only for debugger tracebacks, never for the user message.
            raise ConfigParseError.invalid_yaml() from exc

    if not isinstance(document, dict) or not isinstance(document.get("databases"), dict):
        raise ConfigParseError.invalid_shape()

    profiles: list[ConnectionProfile] = []
    for name, connection_string in document["databases"].items():
        profiles.append(ConnectionProfile(name=name, connection_string=connection_string))
    return profiles
