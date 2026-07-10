"""Load and validate connection profiles from a local YAML config file.

Fail-fast gates: missing file, malformed/wrong-shape YAML, exact-duplicate
YAML keys, blank name, case-insensitive duplicate name, blank connection
string. Leading/trailing whitespace is trimmed from both `name` and
`connection_string` before validation.
"""

import os

import yaml

from schema_comparator.config.errors import (
    ConfigFileNotFoundError,
    ConfigParseError,
    ProfileValidationError,
)
from schema_comparator.config.models import ConnectionProfile


class _DuplicateKeyLoader(yaml.SafeLoader):
    """A SafeLoader that raises on exact-duplicate mapping keys.

    Plain `yaml.safe_load` silently keeps the last value when a mapping has
    two identical keys, which would defeat the spec's "re-declared identical
    YAML key" duplicate-profile scenario. This subclass raises before the
    dict collapses the duplicate.
    """


def _no_duplicate_keys(loader: yaml.SafeLoader, node: yaml.Node, deep: bool = False) -> dict:
    seen: set[object] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise ProfileValidationError.duplicate_name(str(key))
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


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
            document = yaml.load(handle, Loader=_DuplicateKeyLoader)
        except yaml.YAMLError as exc:
            # Never embed str(exc): PyYAML error text can echo a snippet of
            # the offending line/connection-string fragment. Chain `from
            # exc` only for debugger tracebacks, never for the user message.
            raise ConfigParseError.invalid_yaml() from exc

    if not isinstance(document, dict) or not isinstance(document.get("databases"), dict):
        raise ConfigParseError.invalid_shape()

    profiles: list[ConnectionProfile] = []
    seen_casefolded_names: set[str] = set()
    for raw_name, raw_connection_string in document["databases"].items():
        name = str(raw_name).strip()
        connection_string = str(raw_connection_string).strip()

        if not name:
            raise ProfileValidationError.empty_name()

        casefolded_name = name.casefold()
        if casefolded_name in seen_casefolded_names:
            raise ProfileValidationError.duplicate_name(name)
        seen_casefolded_names.add(casefolded_name)

        if not connection_string:
            raise ProfileValidationError.empty_connection_string(name)

        profiles.append(ConnectionProfile(name=name, connection_string=connection_string))
    return profiles
