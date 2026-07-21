"""Profile parser for MySQL and MariaDB providers."""

import urllib.parse
from typing import Any

from schema_comparator.config.errors import ProfileValidationError
from schema_comparator.config.models import ConnectionProfile


def validate_mysql_family_profile(profile: ConnectionProfile, provider_name: str = "mysql") -> None:
    """Validate connection profile options for MySQL / MariaDB."""
    if not profile.connection_string and "database" not in profile.options:
        raise ProfileValidationError(
            f"El perfil '{profile.name}' para '{provider_name}' debe definir una cadena de conexión "
            "o especificar 'database' en las opciones."
        )


def parse_mysql_family_options(profile: ConnectionProfile) -> dict[str, Any]:
    """Parse connection options from profile options or connection_string (pymysql format)."""
    options: dict[str, Any] = {}

    if profile.connection_string:
        cs = profile.connection_string
        if cs.startswith("mysql://") or cs.startswith("mariadb://"):
            url = urllib.parse.urlparse(cs)
            if url.hostname:
                options["host"] = url.hostname
            if url.port:
                options["port"] = url.port
            if url.username:
                options["user"] = url.username
            if url.password:
                options["password"] = urllib.parse.unquote(url.password)
            if url.path and len(url.path) > 1:
                options["database"] = url.path[1:]
        else:
            # Simple key=value string parser
            parts = [p.strip() for p in cs.split(";") if p.strip()]
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    k_lower = k.strip().lower()
                    v_val = v.strip()
                    if k_lower in ("server", "host", "data source"):
                        options["host"] = v_val
                    elif k_lower in ("port",):
                        options["port"] = int(v_val)
                    elif k_lower in ("database", "initial catalog", "db"):
                        options["database"] = v_val
                    elif k_lower in ("uid", "user", "user id", "username"):
                        options["user"] = v_val
                    elif k_lower in ("pwd", "password"):
                        options["password"] = v_val

    # Override/supplement with explicit profile options if provided
    for key, val in profile.options.items():
        options[key] = val

    return options
