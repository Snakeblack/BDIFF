"""Load and persist connection profiles (YAML). Never logs secrets."""

from schema_comparator.config.errors import (
    ConfigError,
    ConfigFileNotFoundError,
    ConfigParseError,
    ProfileValidationError,
)
from schema_comparator.config.loader import load_profiles
from schema_comparator.config.models import ConnectionProfile

__all__ = [
    "ConnectionProfile",
    "load_profiles",
    "ConfigError",
    "ConfigFileNotFoundError",
    "ConfigParseError",
    "ProfileValidationError",
]
